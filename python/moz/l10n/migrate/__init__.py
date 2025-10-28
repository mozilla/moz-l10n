from __future__ import annotations

import dataclasses
from logging import getLogger
from os.path import isdir, isfile, join
from typing import Callable, Tuple

from moz.l10n.formats import Format, detect_format
from moz.l10n.model import (
    CatchallKey,
    Entry,
    Message,
    PatternMessage,
    Resource,
    Section,
    SelectMessage,
)
from moz.l10n.paths import L10nConfigPaths, L10nDiscoverPaths
from moz.l10n.paths.android_locale import get_android_locale
from moz.l10n.resource import parse_resource, serialize_resource

from .utils import MigrationContext, get_entry, get_pattern, insert_entry_after

log = getLogger(__name__)


def apply_migration(
    paths: str | L10nConfigPaths | L10nDiscoverPaths,
    add_entries: dict[
        str,
        dict[
            tuple[str, ...] | str,
            Callable[
                [Resource[Message], MigrationContext],
                Message
                | Entry[Message]
                | Tuple[Message | Entry[Message], set[str] | set[tuple[str, ...]]]
                | None,
            ],
        ],
    ],
) -> None:
    """
    Adds entries to resources in `paths`.

    `add_entries` is a mapping of resource reference paths to target entry identifiers
    to functions that define their values;
    the function will be called with two arguments `(resource, context: MigrationContext)`.

    Functions defining new entries should return a Message, an Entry,
    or a tuple consisting of one of those along with a set of identifiers
    for entries after which the new entry should be inserted.

    If an entry already exists with the target identifier, it is not modified.

    If no resource exists for a target locale, one is created.
    For .ini, JSON, and XML-based resources,
    the reference resource must exist to create a new resource.
    """
    if isinstance(paths, str):
        if isdir(paths):
            paths = L10nDiscoverPaths(paths)
        elif isfile(paths):
            paths = L10nConfigPaths(
                paths, locale_map={"android_locale": get_android_locale}
            )
        else:
            raise ValueError(f"Not found: {paths}")
    for ref_path, res_add_entries in add_entries.items():
        tgt_fmt, locales = paths.target(ref_path)
        if tgt_fmt is None:
            raise ValueError(f"Invalid reference path: {ref_path}")

        src_res: Resource[Message] | None = None
        for locale in locales:
            ctx = MigrationContext(paths, ref_path, locale)
            res = ctx.get_resource(ref_path)
            if res is None:
                if src_res is None:
                    src_res = _get_empty_resource(join(paths.ref_root, ref_path))
                    if src_res is None:
                        log.warning(
                            f"Failed to parse source resource for {ref_path} (required for {locale})"
                        )
                        continue
                res = dataclasses.replace(src_res)

            changed = 0
            for id, create in res_add_entries.items():
                if isinstance(id, str):
                    id = (id,)
                if _create_entry(res, ctx, id, create):
                    changed += 1

            if changed:
                log.debug(f"Updating {ref_path} for locale {locale}")
                tgt_path = paths.format_target_path(tgt_fmt, locale)
                with open(tgt_path, "w", encoding="utf-8") as file:
                    for line in serialize_resource(res):
                        file.write(line)


def copy(
    ref_path: None | str,
    id: tuple[str, ...] | str,
    variant: tuple[str | CatchallKey, ...] | str | None = None,
) -> Callable[
    [Resource[Message], MigrationContext],
    tuple[Entry[Message] | Message, set[tuple[str, ...]]] | None,
]:
    """
    Create a copy migration function, from entry `id` in `ref_path`.

    If `ref_path` is None, the entry is copied from the current Resource.

    If `variant` is set and `id` contains a SelectMessage,
    the pattern of the specified variant is copied (or the default one).
    """
    if isinstance(id, str):
        id = (id,)

    def copy_(
        res: Resource[Message], ctx: MigrationContext
    ) -> tuple[Entry[Message] | Message, set[tuple[str, ...]]] | None:
        if ref_path:
            res_ = ctx.get_resource(ref_path)
            if res_ is None:
                return None
        else:
            res_ = res

        if variant is None:
            entry = get_entry(res_, *id)
            return (entry, {id}) if entry else None

        try:
            pattern = get_pattern(res_, *id, variant=variant)
            return PatternMessage(pattern), {id}
        except StopIteration:
            return None

    return copy_


def _get_empty_resource(path: str) -> Resource[Message] | None:
    format = detect_format(path)

    res = None
    if format is None or format in {Format.ini, Format.xliff}:
        try:
            res = parse_resource(path)
            format = res.format
            assert format
        except Exception:
            return None

    if format in {Format.ini, Format.xliff}:
        assert res
        for section in res.sections:
            section.entries.clear()
        return res

    return Resource(format, [Section((), [])])


def _create_entry(
    res: Resource[Message],
    ctx: MigrationContext,
    id: tuple[str, ...],
    create: Callable[
        [Resource[Message], MigrationContext],
        Message
        | Entry[Message]
        | Tuple[Message | Entry[Message], set[tuple[str, ...]] | set[str]]
        | None,
    ],
) -> bool:
    """
    Adds entry `id` to `res`, created with the `create` function.

    The `create` function will be called with two arguments `(res: Resource, ctx: MigrationContext)`.
    It should return a Message, an Entry, or a tuple consisting of one of those,
    along with a set of identifiers for entries after which the new entry should be inserted.

    If an `id` entry already exists, it is not modified.

    Returns `True` on success.
    """

    if get_entry(res, *id) is not None:
        log.debug(f"Already defined: {ctx.pretty_id(id)}")
        return False

    try:
        src_entry = create(res, ctx)
    except StopIteration:
        log.debug(f"Source not found: {ctx.pretty_id(id)}")
        return False

    if src_entry is None:
        return False

    if isinstance(src_entry, tuple):
        src_ids = src_entry[1]
        src_entry = src_entry[0]
    elif isinstance(src_entry, Entry):
        src_ids = {src_entry.id}
    else:
        src_ids = {id}

    # For .ini and .xliff, new_entry.id will initially contain the section id.
    # This is dropped later in insert_entry_after().
    if isinstance(src_entry, Entry):
        new_entry = dataclasses.replace(src_entry, id=id)
    elif isinstance(src_entry, (PatternMessage, SelectMessage)):
        new_entry = Entry(id, src_entry)
    else:
        raise ValueError(
            f"Unsupported entry type {type(src_entry)}: {ctx.pretty_id(id)}"
        )

    insert_entry_after(res, new_entry, *src_ids)
    return True
