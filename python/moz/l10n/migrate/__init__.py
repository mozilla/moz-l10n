# Copyright Mozilla Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import dataclasses
from copy import deepcopy
from logging import getLogger
from os.path import isdir, isfile, join
from typing import Callable

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

all_migrations: list[Migrate] = []


class Migrate:
    paths: L10nConfigPaths | L10nDiscoverPaths | None = None

    def __init__(
        self,
        map: dict[
            str,
            dict[
                tuple[str, ...] | str,
                Callable[
                    [Resource[Message], MigrationContext],
                    Message
                    | Entry[Message]
                    | tuple[Message | Entry[Message], set[str] | set[tuple[str, ...]]]
                    | None,
                ],
            ],
        ],
        paths: str | L10nConfigPaths | L10nDiscoverPaths | None = None,
    ) -> None:
        """
        Define a migration that adds entries according to `map` to resources in `paths`.

        This is primarily intended to be called from a migration script,
        which is then processed with the `l10n-migrate` CLI command.

        `map` is a mapping of resource reference paths to entry identifiers
        to functions that define their values;
        the function will be called with two positional arguments
        `(resource, context: MigrationContext)`.

        Functions defining new entries should return a Message, an Entry,
        or a tuple consisting of one of those along with a set of identifiers
        for entries after which the new entry should be inserted.

        If `paths` is a string, it needs to be either a path to a directory
        or a path to an l10n config file.
        This may also be set by an `l10n-migrate` CLI argument.
        """
        self.map = map
        if paths is not None:
            self.set_paths(paths)
        all_migrations.append(self)

    def set_paths(self, paths: str | L10nConfigPaths | L10nDiscoverPaths) -> None:
        """
        If `paths` is a string, it needs to be either a path to a directory
        or a path to an l10n config file.
        """
        if isinstance(paths, (L10nConfigPaths, L10nDiscoverPaths)):
            self.paths = paths
        elif isdir(paths):
            self.paths = L10nDiscoverPaths(paths)
        elif isfile(paths):
            self.paths = L10nConfigPaths(
                paths, locale_map={"android_locale": get_android_locale}
            )
        else:
            raise ValueError(f"Not found: {paths}")

    def apply(self, dry_run: bool = False) -> None:
        """
        Adds entries according to `map` to resources in `paths`.

        If an entry already exists with the target identifier, it is not modified.

        If no resource exists for a target locale, one is created.
        For .ini, JSON, and XML-based resources,
        the reference resource must exist to create a new resource.
        """
        if self.paths is None:
            raise ValueError("Paths not set")
        for ref_path, res_add_entries in self.map.items():
            tgt_fmt, locales = self.paths.target(ref_path)
            if tgt_fmt is None:
                raise ValueError(f"Invalid reference path: {ref_path}")

            src_res: Resource[Message] | None = None
            for locale in locales:
                ctx = MigrationContext(self.paths, ref_path, locale)
                res = ctx.get_resource(ref_path)
                if res is None:
                    if src_res is None:
                        src_res = _get_empty_resource(
                            join(self.paths.ref_root, ref_path)
                        )
                        if src_res is None:
                            log.warning(
                                f"Failed to parse source resource for {ref_path} (required for {locale})"
                            )
                            continue
                    res = deepcopy(src_res)

                changed = 0
                for id, create in res_add_entries.items():
                    if isinstance(id, str):
                        id = (id,)
                    if _create_entry(res, ctx, id, create):
                        changed += 1

                if changed:
                    log.info(f"Updating {ref_path} for locale {locale}")
                    tgt_path = self.paths.format_target_path(tgt_fmt, locale)
                    if not dry_run:
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
                log.debug(f"Copy-from resource not found: {ctx.pretty_id(id)}")
                return None
        else:
            res_ = res

        if variant is None:
            entry = get_entry(res_, *id)
            if entry:
                return (entry, {id})
            else:
                log.debug(f"Copy-from entry not found: {ctx.pretty_id(id)}")
                return None

        try:
            pattern = get_pattern(res_, *id, variant=variant)
            return PatternMessage(pattern), {id}
        except StopIteration:
            log.debug(
                f"Copy-from pattern for variant {variant} not found: {ctx.pretty_id(id)}"
            )
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
        | tuple[Message | Entry[Message], set[tuple[str, ...]] | set[str]]
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
        log.info(f"Already defined: {ctx.pretty_id(id)}")
        return False

    try:
        src_entry = create(res, ctx)
    except StopIteration:
        log.info(f"Source not found: {ctx.pretty_id(id)}")
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
