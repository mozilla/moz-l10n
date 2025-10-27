from __future__ import annotations

import dataclasses
from typing import Callable, Tuple, TypeVar, Union

from moz.l10n.model import (
    CatchallKey,
    Entry,
    Expression,
    Message,
    Pattern,
    PatternMessage,
    Resource,
    Section,
    SelectMessage,
    VariableRef,
)
from moz.l10n.resource import parse_resource, serialize_resource

Ctx = TypeVar("Ctx")
M = TypeVar("M", bound=Union[Message, str])


def get_entry(res: Resource[M], *id: str) -> Entry[M] | None:
    """
    Get an entry matching `id` from `res`.

    If not found, a StopIteration exception is raised
    """
    for section in res.sections:
        if section.id:
            sid_len = len(section.id)
            if section.id != id[:sid_len]:
                continue
            eid = id[sid_len:]
        else:
            eid = id
        entry = next(
            (e for e in section.entries if isinstance(e, Entry) and e.id == eid),
            None,
        )
        if entry is not None:
            return entry
    return None


def get_pattern(
    res: Resource[Message],
    *id: str,
    default: Pattern | None = None,
    keys: tuple[str | CatchallKey, ...] | None = None,
) -> Pattern:
    """
    Get a pattern matching `id` from `res`.

    If the entry for `id` is a PatternMessage, its `.value` is returned.

    If the entry for `id` is a SelectMessage,
    either the pattern matching `keys` is returned,
    or (if not found) the fallback pattern.

    If `default` is a Pattern, it is returned if no matching pattern is found.
    Otherwise, if a StopIteration exception is raised
    """
    entry = get_entry(res, *id)
    if entry is None:
        if default is not None:
            return default
        raise StopIteration

    msg = entry.value
    if isinstance(msg, PatternMessage):
        return msg.pattern
    elif isinstance(msg, SelectMessage):
        if keys in msg.variants:
            return msg.variants[keys]
        return next(
            pattern
            for keys, pattern in msg.variants.items()
            if all(isinstance(key, CatchallKey) for key in keys)
        )

    raise ValueError(f"Value of {id} entry is not a Message")


def insert_entry_after(
    res: Resource[M], entry: Entry[M], *ids: tuple[str, ...] | str
) -> None:
    """
    Insert `entry` in `res` after the last entry
    with an `.id` matching one of `ids`,
    or if none such are found,
    at the end of the last section matching any of `ids`.

    If none such is found, raises StopIteration.
    """
    id_set = {id if isinstance(id, tuple) else (id,) for id in ids}
    last_section: Section[M] | None = None
    for section in reversed(res.sections):
        if section.id:
            sid_len = len(section.id)
            eid_set = {id[sid_len:] for id in id_set if section.id == id[:sid_len]}
            if not eid_set:
                continue
        else:
            eid_set = id_set
        for e_rev_idx, e in enumerate(reversed(section.entries)):
            if isinstance(e, Entry) and e.id in eid_set:
                section.entries.insert(len(section.entries) - e_rev_idx, entry)
                return
        last_section = section
    if last_section is None:
        raise StopIteration
    else:
        last_section.entries.append(entry)


def plural_message(
    var_name: str,
    *,
    zero: Pattern | None = None,
    one: Pattern | None = None,
    two: Pattern | None = None,
    few: Pattern | None = None,
    many: Pattern | None = None,
    other: Pattern,
) -> SelectMessage:
    """
    Construct a SelectMessage using `var_name` to determine the plural category,
    with the given variants.

    By convention, use the following as `var_name`:

    - `"n"` for Gettext plurals
    - `"quantity"` for Android strings.
    """
    raw_variants: list[tuple[str | CatchallKey, Pattern | None]] = [
        ("zero", zero),
        ("one", one),
        ("two", two),
        ("few", few),
        ("many", many),
        (CatchallKey("other"), other),
    ]
    return SelectMessage(
        declarations={var_name: Expression(VariableRef(var_name), "number")},
        selectors=(VariableRef(var_name),),
        variants={
            (key,): pattern for key, pattern in raw_variants if pattern is not None
        },
    )


def apply_migration(
    res: Resource[Message] | str,
    changes: dict[
        tuple[str, ...] | str,
        Callable[
            [Resource[Message], Ctx | None],
            Message
            | Entry[Message]
            | Tuple[Message | Entry[Message], tuple[tuple[str, ...] | str, ...] | str],
        ],
    ],
    context: Ctx | None = None,
) -> int:
    """
    Applies `changes` to a Resource `res`.

    If `res` is a string, the resource at that path is parsed is modified.

    The `changes` are a mapping of target entry identifiers to functions that define their values;
    the function will be called with two arguments `(res: Resource, context: Ctx)`,
    passing through the unmodified `context` given to this function (`None` by default).

    Change functions should return a Message, an Entry, or a tuple consisting of one of those,
    along with one or more identifiers for entries after which the new entry should be inserted.

    If an entry already exists with the target identifier,
    it is not modified.
    """
    if isinstance(res, str):
        res_path = res
        res = parse_resource(res_path)
    else:
        res_path = None
    changed = 0
    for id, change in changes.items():
        if isinstance(id, str):
            id = (id,)

        if get_entry(res, *id) is not None:
            continue

        src_entry = change(res, context)
        if isinstance(src_entry, tuple):
            src_ids = src_entry[1]
            src_entry = src_entry[0]
            if isinstance(src_ids, str):
                src_ids = (src_ids,)
        elif isinstance(src_entry, Entry):
            src_ids = (src_entry.id,)
        else:
            src_ids = (id,)

        if isinstance(src_entry, Entry):
            new_entry = (
                src_entry
                if src_entry.id == id
                else dataclasses.replace(src_entry, id=id)
            )
        elif isinstance(src_entry, (PatternMessage, SelectMessage)):
            new_entry = Entry(id, src_entry)
        else:
            raise ValueError(f"Entry for {id} has unsupported type {type(src_entry)}")

        insert_entry_after(res, new_entry, *src_ids)
        changed += 1
    if changed and res_path:
        with open(res_path, "w", encoding="utf-8") as file:
            for line in serialize_resource(res):
                file.write(line)
    return changed
