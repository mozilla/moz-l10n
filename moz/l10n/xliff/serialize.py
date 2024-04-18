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

from collections.abc import Iterator
from typing import cast

from lxml import etree

from ..message import Expression, Markup, Message, Pattern, PatternMessage, VariableRef
from ..resource import Comment, Metadata, Resource
from .parse import xml_ns


def xliff_serialize(
    resource: Resource[Message | str, str],
    trim_comments: bool = False,
) -> Iterator[str]:
    """
    Serialize a resource as an XLIFF 1.2 file.

    Sections identify files and groups within them,
    with the first identifier part parsed as the <file> "original" attribute,
    and later parts as <group> "id" attributes.

    Metadata keys encode XML element data.
    They have the following shape:

    ```
        key = *path_part ('.' | '!' | xml_id)
        path_part = [digits ','] xml_id) '/'
        xml_id = xml_name | xml_name ':' xml_name
    ```

    Each `path_part` represents a possibly namespaced element.
    The starting `digits` (or any other content in that position) is ignored;
    its only function is to differentiate adjacent elements with the same name.

    A key ending with `.` represents text content,
    and a key ending with `!` represents a comment.
    Other keys represent attribute values.

    The attribute and element names may be of the form `ns:foo`,
    in which case the resource should have an `xmlns:ns` metadata entry
    with its URI value.
    """

    yield '<?xml version="1.0" encoding="utf-8"?>\n'
    if resource.comment and not trim_comments:
        yield f"\n<!--{comment_body(resource.comment, 0)}-->\n\n"

    # The nsmap needs to be set during creation
    # https://bugs.launchpad.net/lxml/+bug/555602
    root_nsmap: dict[str | None, str] = {}
    root_attrib: list[Metadata[str]] = []
    for m in resource.meta:
        k = m.key
        v = m.value
        if k == "xmlns":
            root_nsmap[None] = v
        elif k.startswith("xmlns:"):
            root_nsmap[k[6:]] = v
        else:
            root_attrib.append(m)
    root = etree.Element(
        "xliff",
        attrib={clark_name(root_nsmap, m.key): m.value for m in root_attrib},
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
                assign_metadata(file, section.meta)
                parent = etree.SubElement(file, "body")
            else:
                parent = etree.SubElement(parent, "group", {"id": id_part})
                assign_metadata(parent, section.meta)
            prev[parent_key] = parent
        indent = 2 * len(section.id)
        if section.comment:
            comment = etree.Comment(comment_body(section.comment, indent))
            parent.addprevious(comment)

        indent += 2
        for entry in section.entries:
            if isinstance(entry, Comment):
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

            unit = etree.SubElement(parent, tag, {"id": id})
            assign_metadata(unit, entry.meta)

            msg = entry.value
            target = None
            source = None
            if (
                tag == "trans-unit"
                and msg
                and (
                    isinstance(msg, str)
                    or isinstance(msg, PatternMessage)
                    and msg.pattern
                )
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
                elif msg.declarations:
                    raise ValueError(f"Unsupported message with declarations: {msg}")
                else:
                    set_pattern(target, msg.pattern)

            if entry.comment:
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


def assign_metadata(
    el: etree._Element, meta: list[Metadata[str]], base: str = ""
) -> None:
    key_start = len(base)
    done: list[str] = []
    for m in meta:
        key = m.key[key_start:] if key_start else m.key
        if key == ".":
            if len(el) == 0:
                el.text = (el.text or "") + m.value
            else:
                last = el[-1]
                last.tail = (last.tail or "") + m.value
        elif key == "!":
            el.append(etree.Comment(m.value))
        elif "/" in key:
            if any(m.key.startswith(prev) for prev in done):
                continue
            name_end = key.index("/")
            name = key[0:name_end]
            if "," in name:
                name = name[name.index(",") + 1 :]
            child = etree.SubElement(el, clark_name(el.nsmap, name))
            child_base = base + key[0 : name_end + 1]
            child_meta = [m for m in meta if m.key.startswith(child_base)]
            assign_metadata(child, child_meta, child_base)
            done.append(child_base)
        else:
            el.attrib[clark_name(el.nsmap, key)] = m.value


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


def clark_name(nsmap: dict[str | None, str], name: str) -> str:
    """See https://lxml.de/tutorial.html#namespaces"""
    if ":" not in name:
        return name
    ns, local = name.split(":", 1)
    if ns in nsmap:
        return etree.QName(nsmap[ns], local).text
    if ns == "xml":
        return f"{{{xml_ns}}}{local}"
    raise ValueError(f"Name with unknown namespace: {name}")
