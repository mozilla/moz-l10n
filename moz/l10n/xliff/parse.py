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

from lxml import etree

from ..message import Expression, Markup, Message, PatternMessage, VariableRef
from ..resource import Comment, Entry, Metadata, Resource, Section

xliff_ns = (
    None,
    "urn:oasis:names:tc:xliff:document:1.0",
    "urn:oasis:names:tc:xliff:document:1.1",
    "urn:oasis:names:tc:xliff:document:1.2",
)
xml_ns = "http://www.w3.org/XML/1998/namespace"


def xliff_parse(source: str | bytes) -> Resource[Message, str]:
    """
    Parse an XLIFF 1.2 file into a message resource.

    Sections identify files and groups within them,
    with the first identifier part parsed as the <file> "original" attribute,
    and later parts as <group> "id" attributes.

    An entry's value represents the <target> of a <trans-unit>,
    and its comment the first <note>.
    Other elements and attributes are represented by metadata.

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
    root = etree.fromstring(source.encode() if isinstance(source, str) else source)
    version = root.attrib.get("version", None)
    if version not in ("1.0", "1.1", "1.2"):
        raise ValueError(f"Unsupported <xliff> version: {version}")
    ns = root.nsmap.get(None, None)
    if ns in xliff_ns:
        ns = f"{{{ns}}}" if ns else ""
    else:
        raise ValueError(f"Unsupported namespace: {ns}")

    if root.tag != f"{ns}xliff":
        raise ValueError(f"Unsupported root node: {root}")
    if root.text and not root.text.isspace():
        raise ValueError(f"Unexpected text in <xliff>: {root.text}")

    res: Resource[Message, str] = Resource([])
    root_comments = [
        c.text for c in root.itersiblings(etree.Comment, preceding=True) if c.text
    ]
    if root_comments:
        root_comments.reverse()
        res.comment = comment_str(root_comments)
    res.meta = attrib_as_metadata(root)
    for key, uri in root.nsmap.items():
        res.meta.append(Metadata(f"xmlns:{key}" if key else "xmlns", uri))

    comment: list[str] = []
    for file in root:
        if file.tail and not file.tail.isspace():
            raise ValueError(f"Unexpected text in <xliff>: {file.tail}")
        if isinstance(file, etree._Comment):
            comment.append(file.text)
        elif file.tag == f"{ns}file":
            file_name = file.attrib.get("original", None)
            if file_name is None:
                raise ValueError(f'Missing "original" attribute for <file>: {file}')
            meta = attrib_as_metadata(file, None, ("original",))
            entries: list[Entry[Message, str] | Comment] = []
            body = None
            for child in file:
                if isinstance(child, etree._Comment):
                    entries.append(Comment(comment_str(child.text)))
                elif child.tag == f"{ns}header":
                    meta += element_as_metadata(child, "header/", True)
                elif child.tag == f"{ns}body":
                    if body:
                        raise ValueError(f"Duplicate <body> in <file>: {file}")
                    body = child
                else:
                    raise ValueError(
                        f"Unsupported <{child.tag}> element in <file>: {file}"
                    )
                if child.tail and not child.tail.isspace():
                    raise ValueError(f"Unexpected text in <file>: {child.tail}")

            section = Section([file_name], entries, meta=meta)
            if comment:
                section.comment = comment_str(comment)
                comment.clear()
            res.sections.append(section)

            if body is None:
                raise ValueError(f"Missing <body> in <file>: {file}")
            elif body.text and not body.text.isspace():
                raise ValueError(f"Unexpected text in <body>: {body.text}")
            for unit in body:
                if isinstance(unit, etree._Comment):
                    entries.append(Comment(comment_str(unit.text)))
                elif unit.tag == f"{ns}trans-unit":
                    entries.append(parse_trans_unit(unit))
                elif unit.tag == f"{ns}bin-unit":
                    entries.append(parse_bin_unit(unit))
                elif unit.tag == f"{ns}group":
                    res.sections += parse_group(ns, section.id, unit)
                else:
                    raise ValueError(
                        f"Unsupported <{unit.tag}> element in <body>: {body}"
                    )
                if unit.tail and not unit.tail.isspace():
                    raise ValueError(f"Unexpected text in <body>: {unit.tail}")
    return res


def parse_group(
    ns: str, parent: list[str], group: etree._Element
) -> Iterator[Section[Message, str]]:
    id = group.attrib.get("id", "")
    path = parent + [id]
    meta = attrib_as_metadata(group, None, ("id",))
    entries: list[Entry[Message, str] | Comment] = []
    if group.text and not group.text.isspace():
        raise ValueError(f"Unexpected text in <group>: {group.text}")

    # Note that this is modified after being emitted,
    # To ensure that nested groups are ordered by path
    yield Section(path, entries, meta=meta)

    for idx, unit in enumerate(group):
        if isinstance(unit, etree._Comment):
            entries.append(Comment(comment_str(unit.text)))
        elif unit.tag == f"{ns}trans-unit":
            entries.append(parse_trans_unit(unit))
        elif unit.tag == f"{ns}bin-unit":
            entries.append(parse_bin_unit(unit))
        elif unit.tag == f"{ns}group":
            yield from parse_group(ns, path, unit)
        else:
            name = pretty_name(unit, unit.tag)
            meta += element_as_metadata(unit, f"{idx},{name}/", True)
        if unit.tail and not unit.tail.isspace():
            raise ValueError(f"Unexpected text in <group>: {unit.tail}")


def parse_bin_unit(unit: etree._Element) -> Entry[Message, str]:
    id = unit.attrib.get("id", None)
    if id is None:
        raise ValueError(f'Missing "id" attribute for <bin-unit>: {unit}')
    meta = attrib_as_metadata(unit, None, ("id",))
    meta += element_as_metadata(unit, "", False)
    msg = PatternMessage([Expression(None, attributes={"bin-unit": None})])
    return Entry([id], msg, meta=meta)


def parse_trans_unit(unit: etree._Element) -> Entry[Message, str]:
    id = unit.attrib.get("id", None)
    if id is None:
        raise ValueError(f'Missing "id" attribute for <trans-unit>: {unit}')
    meta = attrib_as_metadata(unit, None, ("id",))
    if unit.text and not unit.text.isspace():
        raise ValueError(f"Unexpected text in <trans-unit>: {unit.text}")

    target = None
    note = None
    for idx, el in enumerate(unit):
        if isinstance(el, etree._Comment):
            meta.append(Metadata("!", el.text))
        else:
            q = etree.QName(el.tag)
            name = q.localname if q.namespace in xliff_ns else q.text
            if name == "target":
                if target:
                    raise ValueError(f"Duplicate <target> in <trans-unit> {id}: {unit}")
                target = el
                meta += attrib_as_metadata(el, "target/")
            elif name == "note" and note is None and el.text:
                note = el
                note_attrib = attrib_as_metadata(el, "note/")
                if note_attrib:
                    meta += note_attrib
                elif idx < len(el) - 1:
                    # If there are elements after this <note>,
                    # add a marker for its relative position.
                    meta.append(Metadata("note/.", ""))
            else:
                base = (
                    f"{name}/"
                    if name in ("source", "seg-source")
                    else f"{idx},{pretty_name(el, el.tag)}/"
                )
                meta += element_as_metadata(el, base, True)
        if el.tail and not el.tail.isspace():
            raise ValueError(f"Unexpected text in <body>: {el.tail}")

    comment = "" if note is None else note.text or ""
    msg = PatternMessage([] if target is None else list(parse_pattern(target)))
    return Entry([id], msg, comment, meta)


def parse_pattern(el: etree._Element) -> Iterator[str | Markup]:
    if el.text:
        yield el.text
    for child in el:
        q = etree.QName(child.tag)
        name = q.localname if q.namespace in xliff_ns else q.text
        options: dict[str, str | VariableRef] = dict(child.attrib)
        if name in ("x", "bx", "ex"):
            yield Markup("standalone", name, options)
        elif isinstance(child.tag, str):
            yield Markup("open", name, options)
            yield from parse_pattern(child)
            yield Markup("close", name)
        if child.tail:
            yield child.tail


dash_indent = compile(r" .+(\n   - .*)+ ")


def comment_str(body: list[str] | str) -> str:
    if isinstance(body, str):
        body = [body]
    lines: list[str] = []
    for comment in body:
        if comment:
            if dash_indent.fullmatch(comment):
                # A dash is considered as a part of the indent if it's aligned
                # with the last dash of <!-- in a top-level comment.
                lines.append(comment.replace("\n   - ", "\n").strip(" "))
            else:
                lines.append(
                    "\n".join(line.strip() for line in comment.splitlines()).strip("\n")
                )
    return "\n\n".join(lines).strip("\n")


def element_as_metadata(
    el: etree._Element, base: str, with_attrib: bool
) -> Iterator[Metadata[str]]:
    is_empty = True
    if with_attrib:
        am = attrib_as_metadata(el, base)
        if am:
            yield from am
            is_empty = False
    if el.text and not el.text.isspace():
        yield Metadata(f"{base}.", el.text)
        is_empty = False
    for idx, child in enumerate(el):
        if isinstance(child, etree._Comment):
            yield Metadata(f"{base}!", child.text)
        elif isinstance(child.tag, str):
            name = pretty_name(child, child.tag)
            yield from element_as_metadata(child, f"{base}{idx},{name}/", True)
        else:
            raise ValueError(f"Unsupported metadata element at {base}{idx}: {el}")
        if child.tail and not child.tail.isspace():
            yield Metadata(f"{base}.", child.tail)
        is_empty = False
    if is_empty and with_attrib:
        yield Metadata(f"{base}.", "")


def attrib_as_metadata(
    el: etree._Element, base: str | None = None, exclude: tuple[str] | None = None
) -> list[Metadata[str]]:
    res = []
    for key, value in el.attrib.items():
        if not exclude or key not in exclude:
            pk = pretty_name(el, key)
            res.append(Metadata(base + pk if base else pk, value))
    return res


def pretty_name(el: etree._Element, name: str) -> str:
    if not name.startswith("{"):
        return name
    q = etree.QName(name)
    ns = q.namespace
    if ns in xliff_ns:
        return q.localname
    if ns == xml_ns:
        return f"xml:{q.localname}"
    ns_key = next(iter(k for k, v in el.nsmap.items() if v == ns), None)
    if ns_key:
        return f"{ns_key}:{q.localname}"
    else:
        raise ValueError(f"Name with unknown namespace: {name}")
