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
from re import compile
from typing import Any, cast

from lxml import etree

from ..message import (
    CatchallKey,
    Expression,
    FunctionAnnotation,
    Markup,
    Message,
    Pattern,
    PatternMessage,
    SelectMessage,
    VariableRef,
)
from ..resource import Entry, Metadata, Resource
from .parse import plural_categories, xml_name


def android_serialize(
    resource: Resource[Message | str, Any],
    trim_comments: bool = False,
) -> Iterator[str]:
    """
    Serialize a resource as an Android strings XML file.

    Section comments and metadata are not supported.
    Resource and entry metadata must be stringifiable,
    as they're stored in XML attributes.

    Messages in '!ENTITY' sections are included in a !DOCTYPE declaration.
    Otherwise, sections must be anonymous.

    Multi-part message identifiers are only supported for <string-array>
    values, for which the second part must be convertible to an int.

    Except for "entity", function annotations are ignored.
    Expression and markup attributes are ignored.
    Non-entity expressions are not supported together with Markup.

    Yields the entire XML result as a single string.
    """

    yield '<?xml version="1.0" encoding="utf-8"?>\n'
    if resource.comment and not trim_comments:
        yield f"\n<!--{comment_body(resource.comment, 0)}-->\n\n"

    entities = ""
    root = etree.Element(
        "resources", attrib={m.key: str(m.value) for m in resource.meta}
    )
    string_array = None
    for section in resource.sections:
        if section.meta:
            raise ValueError("Section metadata is not supported")
        if section.comment and not trim_comments:
            add_comment(root, section.comment, True)
        if section.id:
            if section.id == ["!ENTITY"]:
                for entry in section.entries:
                    if isinstance(entry, Entry):
                        entities += "\n  " + entity_definition(entry)
                continue
            else:
                raise ValueError(f"Unsupported section id: {section.id}")

        for entry in section.entries:
            if isinstance(entry, Entry):
                if len(entry.id) not in (1, 2):
                    raise ValueError(f"Unsupported entry id: {entry.id or entry}")
                name = entry.id[0]
                if not xml_name.fullmatch(name):
                    raise ValueError(f"Invalid entry name: {name}")
                if len(entry.id) == 1:
                    attrib = get_attrib(name, entry.meta)
                    if isinstance(entry.value, SelectMessage):
                        # <plurals>
                        el = etree.SubElement(root, "plurals", attrib=attrib)
                        if entry.comment and not trim_comments:
                            add_comment(el, entry.comment, False)
                        set_plural_message(el, entry.value)
                    else:
                        # <string>
                        if entry.comment and not trim_comments:
                            add_comment(root, entry.comment, False)
                        el = etree.SubElement(root, "string", attrib=attrib)
                        set_pattern_message(el, entry.value)
                else:
                    # <string-array>
                    if string_array is None or name != string_array.get("name"):
                        string_array = etree.SubElement(
                            root, "string-array", attrib=get_attrib(name, entry.meta)
                        )
                    if entry.comment and not trim_comments:
                        add_comment(string_array, entry.comment, False)
                    set_string_array_item(string_array, entry)
            elif not trim_comments:
                add_comment(string_array or root, entry.comment, True)

    # Can't use the built-in pretty-printing,
    # as standalone comments need a trailing empty line.
    if len(root) == 0:
        root.text = "\n"
    else:
        root.text = "\n  "
        for el in root:
            if not el.tail:
                el.tail = "\n  "
            if el.tag in ("plurals", "string-array"):
                if len(el) == 0:
                    el.text = "\n  "
                else:
                    el.text = "\n    "
                    for item in el:
                        item.tail = "\n    "
                    el[-1].tail = "\n  "
        root[-1].tail = "\n"

    if entities:
        yield f"<!DOCTYPE resources [{entities}\n]>\n"
    yield etree.tostring(root, encoding="unicode", method="html")
    yield "\n"


def get_attrib(name: str, meta: list[Metadata[Any]]) -> dict[str, str]:
    res = {"name": name}
    for m in meta:
        if m.key == "name":
            raise ValueError(f'Unsupported "name" metadata for {name}')
        res[m.key] = str(m.value)
    return res


def comment_body(content: str, indent: int) -> str:
    # Comments can't include --, so add a zero width space between and after dashes beyond the first
    cc = content.strip().replace("--", "-\u200b-\u200b")
    if "\n" in cc:
        sp = " " * (indent + 2)
        ci = "\n".join(sp + line if line else "" for line in cc.split("\n"))
        return f"\n{ci}\n{' ' * indent}"
    else:
        return f" {cc} "


def add_comment(el: etree._Element, content: str, standalone: bool) -> None:
    indent = 2 if el.tag == "resources" else 4
    comment = etree.Comment(comment_body(content, indent))
    comment.tail = ("\n\n" if standalone else "\n") + (" " * indent)
    el.append(comment)


def entity_definition(entry: Entry[Message | str, Any]) -> str:
    if len(entry.id) != 1 or not xml_name.fullmatch(entry.id[0]):
        raise ValueError(f"Invalid entity identifier: {entry.id}")
    name = entry.id[0]
    if not xml_name.fullmatch(name):
        raise ValueError(f"Invalid entity name: {name}")

    # Characters not allowed in XML EntityValue text
    escape = str.maketrans({"&": "&amp;", "%": "&#37;", '"': "&quot;"})

    if isinstance(entry.value, str):
        value = entry.value.translate(escape)
    elif isinstance(entry.value, PatternMessage) and not entry.value.declarations:
        value = ""
        for part in entry.value.pattern:
            if isinstance(part, str):
                value += part.translate(escape)
            else:
                ref = entity_name(part) if isinstance(part, Expression) else None
                if ref and xml_name.fullmatch(ref):
                    value += f"&{ref};"
                else:
                    raise ValueError(f"Unsupported entity part: {part}")
    else:
        raise ValueError(f"Unsupported entity value: {entry.value}")

    return f'<!ENTITY {name} "{value}">'


def set_string_array_item(
    parent: etree._Element, entry: Entry[Message | str, Any]
) -> None:
    try:
        num = int(entry.id[1])
    except ValueError:
        raise ValueError(f"Unsupported entry id: {entry.id}")
    if num != len(parent):
        raise ValueError(f"String-array keys must be ordered: {entry.id}")
    if isinstance(entry.value, SelectMessage):
        raise ValueError(f"Unsupported message type for {entry.id}: {entry.value}")
    item = etree.SubElement(parent, "item")
    set_pattern_message(item, entry.value)


def set_plural_message(plurals: etree._Element, msg: SelectMessage) -> None:
    sel = msg.selectors[0] if len(msg.selectors) == 1 else None
    if (
        msg.declarations
        or not sel
        or not isinstance(sel.annotation, FunctionAnnotation)
        or sel.annotation.name != "number"
    ):
        raise ValueError(f"Unsupported message: {msg}")
    for keys, value in msg.variants.items():
        key = keys[0] if len(keys) == 1 else None
        if isinstance(key, CatchallKey):
            key = key.value or "other"
        if key not in plural_categories:
            raise ValueError(f"Unsupported plural variant key: {keys}")
        item = etree.SubElement(plurals, "item", attrib={"quantity": key})
        set_pattern(item, value)
        item.tail = "\n    "
    item.tail = "\n  "


def set_pattern_message(el: etree._Element, msg: PatternMessage | str) -> None:
    if isinstance(msg, str):
        el.text = escape_str(msg).replace("\x00", r"\u0000")
    elif isinstance(msg, PatternMessage) and not msg.declarations:
        set_pattern(el, msg.pattern)
    else:
        raise ValueError(f"Unsupported message: {msg}")


def set_pattern(el: etree._Element, pattern: Pattern) -> None:
    node: etree._Element | None
    if any(isinstance(part, Markup) for part in pattern):
        # For HTML content, do not apply Android escaping
        # but do build a proper nested tree of elements.
        parent = el
        node = None
        for part in pattern:
            if isinstance(part, str):
                if node is None:
                    parent.text = parent.text + part if parent.text else part
                else:
                    node.tail = node.tail + part if node.tail else part
            elif isinstance(part, Expression):
                ent_name = entity_name(part)
                if ent_name:
                    node = etree.Entity(ent_name)
                    parent.append(node)
                else:
                    raise ValueError(f"Unsupported expression: {part}")
            elif any(isinstance(value, VariableRef) for value in part.options.values()):
                raise ValueError(f"Unsupported markup with variable option: {part}")
            else:
                attrib = cast(dict[str, str], part.options)
                if part.kind == "standalone":
                    node = etree.SubElement(parent, part.name, attrib=attrib)
                elif part.kind == "open":
                    parent = etree.SubElement(parent, part.name, attrib=attrib)
                    node = None
                elif parent != el and part.name == parent.tag:  # kind == 'close'
                    node = parent
                    parent = cast(etree._Element, parent.getparent())
                else:
                    raise ValueError(f"Improper element nesting for {part} in {parent}")
    else:
        # We're building a single string, but it may include XML entity references.
        # To still apply escaping to the whole string at once
        # (and thereby detect a need to "quote" it),
        # we first build the string with NUL as a sentinel value for entities
        # (and literal null characters), then escape it, and then
        # insert the entity references as appropriate.
        src = ""
        entities: list[str | etree._Entity] = []
        for part in pattern:
            if isinstance(part, str):
                src += part
                nulls = part.count("\x00")
                if nulls:
                    entities += (r"\u0000",) * nulls
            elif isinstance(part, Expression):
                ent_name = entity_name(part)
                if ent_name:
                    entities.append(etree.Entity(ent_name))
                    src += "\x00"
                elif isinstance(part.arg, str):
                    src += part.arg
                elif isinstance(part.arg, VariableRef):
                    src += part.arg.name
                else:
                    raise ValueError(f"Unsupported expression: {part}")
        res = escape_str(src)
        if not entities:
            el.text = res
        elif all(isinstance(ent, str) for ent in entities):
            el.text = res.replace("\x00", r"\u0000")
        else:
            strings = res.split("\x00")
            el.text = strings.pop(0)
            node = None
            for ent, string in zip(entities, strings, strict=True):
                if isinstance(ent, str):
                    if node:
                        node.tail += ent + string  # type: ignore[operator]
                    else:
                        el.text += ent + string
                else:
                    node = ent
                    node.tail = string
                    el.append(node)


def entity_name(part: Expression) -> str | None:
    if (
        isinstance(part.annotation, FunctionAnnotation)
        and part.annotation.name == "entity"
    ):
        name = part.arg.name if isinstance(part.arg, VariableRef) else None
        if name:
            return name
        else:
            raise ValueError(f"Invalid entity exression: {part}")
    return None


# Special Android characters
android_escape = str.maketrans(
    {"\\": r"\u0092", "@": r"\@", "?": r"\?", "\n": r"\n", "\t": r"\t", '"': r"\""}
)

# Control codes are not valid in XML, and nonstandard whitespace is hard to see.
# Not including NUL here because that's used as a stand-in for entities.
control_chars_re = compile(r"[\x01-\x19\x7F-\x9F]|[^\S ]")

# Content requiring double quotes: multiple spaces and straight apostrophes
quoted_re = compile(r"  |'")


def escape_str(src: str) -> str:
    res = src.translate(android_escape)
    res = control_chars_re.sub(lambda m: f"\\u{ord(m.group()):04d}", res)
    return f'"{res}"' if quoted_re.search(res) else res
