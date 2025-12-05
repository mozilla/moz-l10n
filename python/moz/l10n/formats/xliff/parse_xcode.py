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

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from re import compile
from typing import NoReturn, cast

from lxml import etree

from ...model import (
    CatchallKey,
    Entry,
    Expression,
    Message,
    Metadata,
    Pattern,
    PatternMessage,
    SelectMessage,
    VariableRef,
)
from .common import attrib_as_metadata, element_as_metadata


@dataclass
class XcstringsMsgData:
    base: tuple[list[Metadata], str, Pattern] | None = None
    plural: dict[str, tuple[list[Metadata], str, Pattern]] = field(default_factory=dict)
    device: dict[str, tuple[list[Metadata], str, Pattern]] = field(default_factory=dict)
    substitutions: dict[tuple[str, str], tuple[list[Metadata], str, Pattern]] = field(
        default_factory=dict
    )


@dataclass
class XcodeUnitData:
    unit: etree._Element
    source: etree._Element
    target: etree._Element | None
    notes: list[etree._Element]


@dataclass
class StringsdictPlural:
    var_name: str
    format_key: XcodeUnitData | None
    variants: dict[str, XcodeUnitData]


plural_categories = ("zero", "one", "two", "few", "many", "other")
variant_key = compile(r"%#@([a-zA-Z_]\w*)@")
# https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/Strings/Articles/formatSpecifiers.html
printf = compile(
    r"%([1-9]\$)?(?:#@([a-zA-Z_]\w*)@|[-#+ 0,]?[0-9.]*(?:(?:hh?|ll?|qztj)[douxX]|L[aAeEfFgG]|[@%aAcCdDeEfFgGoOspSuUxX]))"
)
not_first_placeholder = compile(r"%[2-9]\$")


def parse_xliff_xcstrings(
    ns: str, body: etree._Element, from_source: bool
) -> Iterator[Entry[Message]]:
    units: dict[str, XcstringsMsgData] = defaultdict(XcstringsMsgData)
    for unit in body:
        if unit.tag != f"{ns}trans-unit":
            raise ValueError(f"Unsupported <{unit.tag!s}> element in <body>: {body}")
        if "id" not in unit.attrib:
            raise ValueError(f'Missing "id" attribute for <trans-unit>: {unit}')
        if unit.text and not unit.text.isspace():
            raise ValueError(f"Unexpected text in <trans-unit>: {unit.text}")
        parse_xliff_xcstrings_unit(ns, units, unit, from_source)

    for msg_id, data in units.items():
        comments: dict[str, str] = {}
        meta: list[Metadata]
        msg: Message

        def error(message: str) -> NoReturn:
            raise ValueError(f"{message} for Xcode message {msg_id}")

        if data.base:
            if data.plural or data.device:
                error("Unsupported variance")
            meta, comment, pattern = data.base
            if not data.substitutions:
                yield Entry(
                    (msg_id,), PatternMessage(pattern), comment=comment, meta=meta
                )
            else:
                # FIXME
                error("TODO: Substitution placeholders are not yet supported")
        elif data.substitutions:
            error("Unsupported variance")

        elif data.plural:
            if data.device:
                error("Unsupported variance")
            msg = SelectMessage(
                declarations={"plural": Expression(None, "number")},
                selectors=(VariableRef("plural"),),
                variants={},
            )
            entry = Entry((msg_id,), msg)
            sel_ph: Expression | None = None
            for id, (meta, comment, pattern) in data.plural.items():
                if id not in plural_categories:
                    error("Invalid plural category")
                if comment:
                    comments[id] = comment
                for m in meta:
                    m.key = f"{id}/{m.key}"
                entry.meta += meta
                ph = next(
                    (
                        el
                        for el in pattern
                        if isinstance(el, Expression)
                        and isinstance(el.arg, VariableRef)
                        and isinstance(src := el.attributes.get("source", None), str)
                        and not not_first_placeholder.match(src)
                    ),
                    None,
                )
                if ph is not None:
                    if sel_ph is None:
                        sel_ph = replace(ph)
                    elif sel_ph != ph:
                        error("Placeholder mismatch")
                    for el in pattern:
                        if isinstance(el, Expression) and el == sel_ph:
                            el.function = None
                key = id if id != "other" else CatchallKey(id)
                msg.variants[(key,)] = pattern
            if sel_ph is not None:
                sel_ph.attributes = {}
                name = cast(VariableRef, sel_ph.arg).name
                msg.declarations = {name: sel_ph}
                msg.selectors[0].name = name
            if comments:
                comment_values = set(comments.values())
                if len(comments) == len(data.plural) and len(comment_values) == 1:
                    (entry.comment,) = comment_values
                else:
                    entry.comment = "\n\n".join(
                        f"{k}: {v}" for k, v in comments.items()
                    )
            if (CatchallKey(),) not in msg.variants:
                error('Missing "other" variant')
            yield entry

        elif data.device:
            msg = SelectMessage(
                declarations={"device": Expression(None, "device")},
                selectors=(VariableRef("device"),),
                variants={},
            )
            entry = Entry((msg_id,), msg)
            for id, (meta, comment, pattern) in data.device.items():
                if comment:
                    comments[id] = comment
                for m in meta:
                    m.key = f"{id}/{m.key}"
                entry.meta += meta
                key = id if id != "other" else CatchallKey(id)
                msg.variants[(key,)] = pattern
            if comments:
                comment_values = set(comments.values())
                if len(comments) == len(data.device) and len(comment_values) == 1:
                    (entry.comment,) = comment_values
                else:
                    entry.comment = "\n\n".join(
                        f"{k}: {v}" for k, v in comments.items()
                    )
            if (CatchallKey(),) not in msg.variants:
                error('Missing "other" variant')
            yield entry

        else:
            error("Unsupported variance")


def parse_xliff_xcstrings_unit(
    ns: str,
    units: dict[str, XcstringsMsgData],
    unit: etree._Element,
    from_source: bool,
) -> None:
    id_parts = unit.attrib["id"].split("|==|")
    msg_id = id_parts[0]

    unit_data = get_xcode_unit_data(ns, unit)
    source = unit_data.source
    target = unit_data.target
    meta = attrib_as_metadata(unit_data.unit, None, ("id",))
    comments: list[str] = []
    for note in unit_data.notes:
        meta += element_as_metadata(note, "note", True)
        if note.text and not note.text.isspace():
            comments.append(note.text.strip())
    if from_source:
        meta += attrib_as_metadata(source, "source")
        if target is not None:
            meta += element_as_metadata(target, "target", True)
        pattern_src = source.text
    else:
        meta.append(Metadata("source", source.text or ""))
        if target is None:
            pattern_src = None
        else:
            meta += attrib_as_metadata(target, "target")
            pattern_src = target.text
    entry_data: tuple[list[Metadata], str, Pattern] = (
        meta,
        "\n\n".join(comments),
        list(parse_xcode_pattern(pattern_src)),
    )

    if len(id_parts) == 1:
        units[msg_id].base = entry_data
        return
    if len(id_parts) == 2:
        dim, *key = id_parts[1].split(".")
        if dim == "plural":
            if len(key) == 1:
                units[msg_id].plural[key[0]] = entry_data
                return
        elif dim == "substitutions":
            if len(key) == 3 and key[1] == "plural":
                units[msg_id].substitutions[(key[0], key[2])] = entry_data
                return
        elif dim == "device":
            if len(key) == 1:
                units[msg_id].device[key[0]] = entry_data
                return

    raise ValueError(
        f'Unsupported Xcode id syntax in <trans-unit id="{unit.attrib["id"]}">'
    )


def parse_xliff_stringsdict(
    ns: str, body: etree._Element, from_source: bool
) -> list[Entry[SelectMessage]] | None:
    plurals: dict[str, StringsdictPlural] = {}
    for unit in body:
        if unit.tag != f"{ns}trans-unit":
            return None
        if unit.text and not unit.text.isspace():
            raise ValueError(f"Unexpected text in <trans-unit>: {unit.text}")
        id = unit.attrib.get("id", None)
        if id and id.startswith("/") and id.endswith(":dict/:string"):
            # If we get this far, this is clearly trying to be an Xcode plural.
            # Therefore, treat any further deviations as errors.
            parse_xliff_stringsdict_unit(ns, plurals, unit)
        else:
            return None

    entries = []
    for msg_id, plural in plurals.items():
        selector = Expression(
            VariableRef(plural.var_name),
            "number",
            attributes={"source": plural.format_key.source.text}
            if plural.format_key and plural.format_key.source.text
            else {},
        )
        meta: list[Metadata] = []
        if plural.format_key:
            meta += attrib_as_metadata(plural.format_key.unit, "format", ("id",))
            if plural.format_key.target is not None:
                meta += attrib_as_metadata(plural.format_key.target, "format/target")
        msg = SelectMessage(
            declarations={plural.var_name: selector},
            selectors=(VariableRef(plural.var_name),),
            variants={},
        )
        for key, variant in plural.variants.items():
            meta += attrib_as_metadata(variant.unit, key, ("id",))
            if from_source:
                meta += attrib_as_metadata(variant.source, f"{key}/source")
                if variant.target is not None:
                    meta += element_as_metadata(variant.target, f"{key}/target", True)
                pattern_src = variant.source.text
            else:
                meta.append(Metadata(f"{key}/source", variant.source.text or ""))
                if variant.target is None:
                    pattern_src = None
                else:
                    meta += attrib_as_metadata(variant.target, f"{key}/target")
                    pattern_src = variant.target.text
            msg.variants[(CatchallKey("other") if key == "other" else key,)] = list(
                parse_xcode_pattern(pattern_src)
            )
        entries.append(Entry((msg_id,), msg, meta=meta))
    return entries


def parse_xliff_stringsdict_unit(
    ns: str, plurals: dict[str, StringsdictPlural], unit: etree._Element
) -> None:
    id_parts = unit.attrib["id"].split(":dict/")
    msg_id = id_parts[0][1:]

    def error(message: str) -> NoReturn:
        raise ValueError(f"{message} in Xcode plural definition {unit.attrib['id']}")

    unit_data = get_xcode_unit_data(ns, unit)
    if id_parts[1] == "NSStringLocalizedFormatKey":
        if len(id_parts) != 3:
            error("Unexpected Xcode plurals id")
        var_match = variant_key.search(unit_data.source.text or "")
        if var_match is None:
            error("Unexpected <source> value")
        if msg_id in plurals:
            prev = plurals[msg_id]
            if prev.format_key is None:
                prev.format_key = unit_data
            else:
                error("Duplicate NSStringLocalizedFormatKey")
            if var_match[1] != prev.var_name:
                error("Mismatching key values")
        else:
            plurals[msg_id] = StringsdictPlural(var_match[1], unit_data, {})
    else:
        if len(id_parts) != 4:
            error("Unexpected Xcode plurals id")
        var_name = id_parts[1]
        plural_cat = id_parts[2]
        if plural_cat not in plural_categories:
            error("Invalid plural category")
        if msg_id in plurals:
            prev = plurals[msg_id]
            if var_name != prev.var_name:
                error("Mismatching key values")
            if plural_cat in prev.variants:
                error(f"Duplicate {plural_cat}")
            prev.variants[plural_cat] = unit_data
        else:
            plurals[msg_id] = StringsdictPlural(
                var_name, None, variants={plural_cat: unit_data}
            )


def get_xcode_unit_data(ns: str, unit: etree._Element) -> XcodeUnitData:
    def error(message: str) -> NoReturn:
        raise ValueError(f'{message} in Xcode <trans-unit id="{unit.attrib["id"]}">')

    source = None
    target = None
    notes = []
    for el in unit:
        if len(el) > 0:
            error(f"Unexpected child elements of <{el.tag!s}>")
        if el.tag == f"{ns}source":
            if el.attrib:
                error("Unexpected attributes of <source>")
            if source is None:
                source = el
            else:
                error("Duplicate <source>")
        elif el.tag == f"{ns}target":
            if target is None:
                target = el
            else:
                error("Duplicate <target>")
        elif el.tag == f"{ns}note":
            if el.attrib or el.text:
                notes.append(el)
        else:
            error(f"Unexpected <{el.tag!s}>")
        if el.tail and not el.tail.isspace():
            raise ValueError(f"Unexpected text in <trans-unit>: {el.tail}")
    if source is None:
        error("Missing <source>")
    return XcodeUnitData(unit, source, target, notes)


def parse_xcode_pattern(src: str | None) -> Iterator[str | Expression]:
    if not src:
        return
    pos = 0
    for m in printf.finditer(src):
        start = m.start()
        if start > pos:
            yield src[pos:start]
        source = m[0]
        if m[2]:
            yield Expression(
                VariableRef(m[2]), "substitution", attributes={"source": source}
            )
        else:
            format = source[-1]
            if format == "%":
                yield Expression("%", attributes={"source": source})
            else:
                name: str
                func: str | None
                # TODO post-py38: should be a match
                if format in {"c", "C", "s", "S"}:
                    name = "str"
                    func = "string"
                elif format in {"d", "D", "o", "O", "p", "u", "U", "x", "X"}:
                    name = "int"
                    func = "integer"
                elif format in {"a", "A", "e", "E", "f", "g", "G"}:
                    name = "num"
                    func = "number"
                else:
                    name = "arg"
                    func = None
                if m[1]:
                    name += m[1][0]
                yield Expression(VariableRef(name), func, attributes={"source": source})
        pos = m.end()
    if pos < len(src):
        yield src[pos:]
