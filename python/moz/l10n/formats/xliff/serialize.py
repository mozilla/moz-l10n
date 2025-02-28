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

from collections.abc import Iterator
from typing import cast

from lxml import etree

from ...model import (
    CatchallKey,
    Comment,
    Entry,
    Expression,
    Markup,
    Message,
    Metadata,
    Pattern,
    PatternMessage,
    Resource,
    SelectMessage,
    VariableRef,
)
from .common import clark_name


def xliff_serialize(
    resource: Resource[str] | Resource[Message],
    trim_comments: bool = False,
) -> Iterator[str]:
    """
    Serialize a resource as an XLIFF 1.2 file.

    Sections identify files and groups within them,
    with the first identifier part parsed as the <file> "original" attribute,
    and later parts as <group> "id" attributes.

    Metadata keys encode XML element data, using XPath expressions as keys.

    For namespaced attribute and element names of the form `ns:foo`,
    the resource should have an `xmlns:ns` metadata entry with its URI value.

    SelectMessage values are only supported in .stringsdict files,
    and their structure must closely match that generated by parse_xliff().
    """

    yield '<?xml version="1.0" encoding="utf-8"?>\n'
    if resource.comment and not trim_comments:
        yield f"\n<!--{comment_body(resource.comment, 0)}-->\n\n"

    # The nsmap needs to be set during creation
    # https://bugs.launchpad.net/lxml/+bug/555602
    root_nsmap: dict[str | None, str] = {}
    root_attrib: list[Metadata] = []
    for m in resource.meta:
        k = m.key
        v = m.value
        if k == "@xmlns":
            root_nsmap[None] = v
        elif k.startswith("@xmlns:"):
            root_nsmap[k[7:]] = v
        elif k.startswith("@"):
            root_attrib.append(m)
        else:
            raise ValueError(f"Unsupported root metadata key: {k}")
    root = etree.Element(
        "xliff",
        attrib={clark_name(root_nsmap, m.key[1:]): m.value for m in root_attrib},
        nsmap=root_nsmap,
    )

    prev: dict[tuple[str, ...], etree._Element] = {}
    for section in resource.sections:
        if not section.id:
            raise ValueError("Anonymous sections are not supported")
        parent_key = tuple(section.id)
        if parent_key in prev:
            raise ValueError(f"Duplicate section identifier: {parent_key}")
        while parent_key and parent_key not in prev:
            parent_key = parent_key[:-1]
        parent = prev[parent_key] if parent_key else root
        for id_part in section.id[len(parent_key) :]:
            parent_key += (id_part,)
            if parent == root:
                file = etree.SubElement(root, "file", {"original": id_part})
                assign_metadata(file, section.meta, trim_comments)
                parent = etree.SubElement(file, "body")
            else:
                parent = etree.SubElement(parent, "group", {"id": id_part})
                assign_metadata(parent, section.meta, trim_comments)
            prev[parent_key] = parent
        indent = 2 * len(section.id)
        if section.comment:
            comment = etree.Comment(comment_body(section.comment, indent))
            parent.addprevious(comment)

        indent += 2
        for entry in section.entries:
            if isinstance(entry, Comment):
                if not trim_comments:
                    comment_str = comment_body(entry.comment, indent)
                    parent.append(etree.Comment(comment_str))
                continue

            if len(entry.id) != 1:
                raise ValueError(f"Unsupported entry id: {entry.id}")
            id = entry.id[0]
            tag = "trans-unit"

            # <bin-unit>
            if isinstance(entry.value, PatternMessage):
                pattern = entry.value.pattern
                if (
                    len(pattern) == 1
                    and isinstance(pattern[0], Expression)
                    and "bin-unit" in pattern[0].attributes
                ):
                    tag = "bin-unit"

            if isinstance(entry.value, SelectMessage):
                if section.id[0].endswith(".stringsdict"):
                    add_xliff_stringsdict_plural(parent, entry, trim_comments)  # type: ignore [arg-type]
                    continue
                else:
                    fn = section.id[0]
                    raise ValueError(f"Unsupported SelectMessage {id} in file: {fn}")

            unit = etree.SubElement(parent, tag, {"id": id})
            assign_metadata(unit, entry.meta, trim_comments)

            msg = entry.value
            target = None
            source = None
            if (
                tag == "trans-unit"
                and msg
                and (not isinstance(msg, PatternMessage) or msg.pattern)
            ):
                target = unit.find("target")
                if target is None:
                    source = unit.find("source")
                    if source is None:
                        raise ValueError(f"Invalid entry with no source: {entry}")
                    target = etree.Element("target")
                    source.addnext(target)
                if isinstance(msg, str):
                    target.text = msg
                elif isinstance(msg, PatternMessage) and not msg.declarations:
                    set_pattern(target, msg.pattern)
                else:
                    raise ValueError(f"Unsupported message: {msg}")

            if entry.comment and not entry.comment.isspace() and not trim_comments:
                note = unit.find("note")
                if note is None:
                    if target is None:
                        prev_el = unit.find("target") or unit.find("source")
                        if prev_el is None:
                            raise ValueError(f"Invalid entry with no source: {entry}")
                    else:
                        prev_el = target
                    note = etree.Element("note")
                    prev_el.addnext(note)
                note.text = entry.comment

    yield etree.tostring(root, encoding="unicode", pretty_print=True)


def add_xliff_stringsdict_plural(
    parent: etree._Element, entry: Entry[SelectMessage], trim_comments: bool
) -> None:
    if entry.comment:
        raise ValueError(f"Unsupported comment on SelectMessage: {entry.comment}")
    msg = entry.value
    if len(msg.selectors) != 1:
        raise ValueError(f"Exactly one selector is required: {msg.selectors}")
    sel = msg.selector_expressions()[0]
    if not isinstance(sel.arg, VariableRef) or sel.function != "number":
        raise ValueError(f"Unsupported selector: {sel}")

    id = entry.id[0]
    id_base = f"/{id}:dict"
    var_name = sel.arg.name

    sel_source = sel.attributes.get("source", None)
    meta_base = "format/"
    meta = [m for m in entry.meta if m.key.startswith(meta_base)]
    if isinstance(sel_source, str):
        xcode_id = f"{id_base}/NSStringLocalizedFormatKey:dict/:string"
        unit = etree.SubElement(parent, "trans-unit", {"id": xcode_id})
        assign_metadata(unit, meta, trim_comments, meta_base)
        source = unit.find("source")
        if source is None:
            first = unit[0] if len(unit) > 0 else None
            if first:
                source = etree.Element("source")
                first.addprevious(source)
            else:
                source = etree.SubElement(unit, "source")
        source.text = sel_source
        target = unit.find("target")
        if target is None:
            target = etree.Element("target")
            source.addnext(target)
        if not target.text:
            target.text = sel_source
    elif meta:
        raise ValueError(
            f"Format key source is required with format attributes for {id}"
        )

    for keys, pattern in msg.variants.items():
        if len(keys) != 1:
            raise ValueError(f"Unsupported variants keys for {id}: {keys}")
        key = keys[0]
        if isinstance(key, CatchallKey):
            key = key.value or "other"
        text = ""
        for part in pattern:
            if isinstance(part, str):
                text += part
            else:
                part_source = part.attributes.get("source", None)
                if isinstance(part_source, str):
                    text += part_source
                elif isinstance(part, Expression) and part.arg is not None:
                    text += part.arg if isinstance(part.arg, str) else part.arg.name
                else:
                    raise ValueError(f"Unsupported pattern part for {id}: {part}")
        xcode_id = f"{id_base}/{var_name}:dict/{key}:dict/:string"
        unit = etree.SubElement(parent, "trans-unit", {"id": xcode_id})
        meta_base = f"{key}/"
        meta = [m for m in entry.meta if m.key.startswith(meta_base)]
        assign_metadata(unit, meta, trim_comments, meta_base)
        source = unit.find("source")
        if source is None:
            raise ValueError(f"Missing {key}/source metadata for {id}")
        target = unit.find("target")
        if target is None:
            target = etree.Element("target")
            source.addnext(target)
        target.text = text


def assign_metadata(
    el: etree._Element, meta: list[Metadata], trim_comments: bool, base: str = ""
) -> None:
    key_start = len(base)
    done: list[str] = []
    for m in meta:
        key = m.key[key_start:] if key_start else m.key
        if key == "":
            if m.value:
                if len(el) == 0:
                    el.text = (el.text or "") + m.value
                else:
                    last = el[-1]
                    last.tail = (last.tail or "") + m.value
        elif key == "comment()":
            el.append(etree.Comment(m.value))
        elif key.startswith("@"):
            el.attrib[clark_name(el.nsmap, key[1:])] = m.value
        else:
            if "/" in key:
                q = m.key
                name_end = key.index("/")
            else:
                q = f"{m.key}/"
                name_end = len(key)
            if any(q.startswith(prev) for prev in done):
                continue
            name = key[0:name_end]
            if "[" in name:
                name = name[: name.index("[")]
            child_root = base + key[0:name_end]
            child_base = f"{child_root}/"
            child_meta = [
                m for m in meta if m.key == child_root or m.key.startswith(child_base)
            ]
            if not trim_comments or name != "note":
                child = etree.SubElement(el, clark_name(el.nsmap, name))
                assign_metadata(child, child_meta, trim_comments, child_base)
            done.append(child_base)


def comment_body(content: str, indent: int) -> str:
    # Comments can't include --, so add a zero width space between and after dashes beyond the first
    cc = content.strip().replace("--", "-\u200b-\u200b")
    if "\n" in cc:
        sp = " " * (indent + 2)
        ci = "\n".join(sp + line if line else "" for line in cc.split("\n"))
        return f"\n{ci}\n{' ' * indent}"
    else:
        return f" {cc} "


def set_pattern(el: etree._Element, pattern: Pattern) -> None:
    parent = el
    prev = None
    for part in pattern:
        if isinstance(part, str):
            if prev is None:
                parent.text = (parent.text or "") + part
            else:
                prev.tail = (prev.tail or "") + part
        elif isinstance(part, Markup):
            name = clark_name(el.nsmap, part.name)
            if part.kind == "close":
                if part.options:
                    raise ValueError(
                        f"Options on closing markup are not supported: {part}"
                    )
                if parent.tag != name or parent == el:
                    raise ValueError(f"Improper element nesting for {part} in {parent}")
                node = parent
                parent = cast(etree._Element, parent.getparent())
            else:
                attrib = {}
                for key, value in part.options.items():
                    if isinstance(value, VariableRef):
                        raise ValueError(
                            f"Unsupported markup with variable option: {part}"
                        )
                    attrib[clark_name(el.nsmap, key)] = value
                node = etree.SubElement(parent, name, attrib)
                if part.kind == "standalone":
                    prev = node
                else:  # 'open'
                    parent = node
                    prev = None
        elif isinstance(part, Expression):
            raise ValueError(f"Unsupported expression: {part}")
