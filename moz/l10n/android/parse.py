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

from collections.abc import Callable, Iterable, Iterator
from re import DOTALL, compile, fullmatch, sub
from typing import cast

from lxml import etree

from ..message import (
    CatchallKey,
    Expression,
    FunctionAnnotation,
    Markup,
    Message,
    PatternMessage,
    SelectMessage,
    VariableRef,
)
from ..resource import Comment, Entry, Metadata, Resource, Section

plural_categories = ("zero", "one", "two", "few", "many", "other")
xml_name_start = r":A-Z_a-z\xC0-\xD6\xD8-\xF6\xF8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\U00010000-\U000EFFFF"
xml_name_rest = r".0-9\xB7\u0300-\u036F\u203F-\u2040-"
xml_name = compile(f"[{xml_name_start}][{xml_name_start}{xml_name_rest}]*")

# Android string resources contain four different kinds of localizable values:
#
#   - HTML entity declarations,
#     which will be inserted into other strings during XML parsing.
#   - Strings with printf-style variables,
#     which also use "quotes" for special escaping behaviour.
#     These may include HTML as escaped string contents,
#     which will require fromHtml(String) processing
#     after being initially formatted with getString(int, Object...)
#   - Strings with HTML contents, which can't include variables,
#     and are generally used via setText(java.lang.CharSequence).
#   - Strings with ICU MessageFormat contents.
#     These also use "quotes" for special escaping behaviour.
#     ICU MessageFormat strings are not currently detected by this library.
#
# The source contents of each of the above needs to be parsed differently,
# and message strings can be found in <string>, <string-array>, and <plurals>
# elements, each of which also needs different parsing.
#
# For more information, see:
# https://developer.android.com/guide/topics/resources/string-resource


def android_parse(source: str | bytes) -> Resource[Message, str]:
    """
    Parse an Android strings XML file into a message resource.

    If any internal DOCTYPE entities are declared,
    they are included as messages in an "!ENTITY" section.

    Resource and entry attributes are parsed as metadata.

    All XML, Android, and printf escapes are unescaped
    except for %n, which has a platform-dependent meaning.
    """
    parser = etree.XMLParser(resolve_entities=False)
    root = etree.fromstring(
        source.encode() if isinstance(source, str) else source, parser
    )
    if root.tag != "resources":
        raise ValueError(f"Unsupported root node: {root}")
    if root.text and not root.text.isspace():
        raise ValueError(f"Unexpected text in resource: {root.text}")
    res: Resource[Message, str] = Resource([Section([], [])])
    root_comments = [c.text for c in root.itersiblings(etree.Comment, preceding=True)]
    if root_comments:
        root_comments.reverse()
        res.comment = comment_str(root_comments)
    res.meta = [Metadata(k, v) for k, v in root.attrib.items()]
    entries = res.sections[0].entries

    dtd = root.getroottree().docinfo.internalDTD
    if dtd:
        entities: list[Entry[Message, str] | Comment] = []
        for entity in dtd.iterentities():
            name = entity.name
            if not name:
                raise ValueError(f"Unnamed entity: {entity}")
            value: Message = PatternMessage(list(parse_entity(entity.content)))
            entities.append(Entry([name], value))
        if entities:
            res.sections.insert(0, Section(["!ENTITY"], entities))

    comment: list[str | None] = []  # TODO: should be list[str]
    for el in root:
        if el.tail and not el.tail.isspace():
            raise ValueError(f"Unexpected text in resource: {el.tail}")
        if isinstance(el, etree._Comment):
            comment.append(el.text)
            if el.tail and el.tail.count("\n") > 1 and comment:
                entries.append(Comment(comment_str(comment)))
                comment.clear()
        else:
            name = el.attrib.get("name", None)
            if not name:
                raise ValueError(f"Unnamed {el.tag} entry: {el}")
            meta = [Metadata(k, v) for k, v in el.attrib.items() if k != "name"]

            if el.tag == "string":
                value = PatternMessage(list(parse_pattern(el)))
                entries.append(Entry([name], value, comment_str(comment), meta))

            elif el.tag == "plurals":
                if el.text and not el.text.isspace():
                    raise ValueError(f"Unexpected text in {name} plurals: {el.text}")
                value = parse_plurals(name, el, comment.extend)
                entries.append(Entry([name], value, comment_str(comment), meta))

            elif el.tag == "string-array":
                if el.text and not el.text.isspace():
                    raise ValueError(
                        f"Unexpected text in {name} string-array: {el.text}"
                    )
                idx = 0
                for item in el:
                    if isinstance(item, etree._Comment):
                        comment.append(item.text)
                    elif item.tag == "item":
                        value = PatternMessage(list(parse_pattern(item)))
                        ic = comment_str(comment)
                        entries.append(Entry([name, str(idx)], value, ic, meta[:]))
                        comment.clear()
                        idx += 1
                    else:
                        cs = etree.tostring(item, encoding="unicode")
                        raise ValueError(f"Unsupported {name} string-array child: {cs}")
                    if item.tail and not item.tail.isspace():
                        raise ValueError(
                            f"Unexpected text in {name} string-array: {item.tail}"
                        )

            else:
                es = etree.tostring(el, encoding="unicode")
                raise ValueError(f"Unsupported entry: {es}")
            if comment:
                comment.clear()
    return res


def comment_str(body: list[str | None]) -> str:
    lines: list[str] = []
    for comment in body:
        if comment:
            if fullmatch(r" .+(\n   - .*)+ ", comment):
                # A dash is considered as a part of the indent if it's aligned
                # with the last dash of <!-- in a top-level comment.
                lines.append(comment.replace("\n   - ", "\n").strip(" "))
            else:
                lines.append(
                    "\n".join(line.strip() for line in comment.splitlines()).strip("\n")
                )
    return "\n\n".join(lines).strip("\n")


entity_re = compile(f"&({xml_name.pattern});")


def parse_entity(src: str | None) -> Iterator[str | Expression]:
    if src:
        pos = 0
        for m in entity_re.finditer(src):
            start = m.start()
            if start > pos:
                yield src[pos:start]
            yield Expression(VariableRef(m[1]), FunctionAnnotation("entity"))
            pos = m.end()
        if pos < len(src):
            yield src[pos:]


def parse_plurals(
    name: str, el: etree._Element, add_comment: Callable[[Iterable[str | None]], None]
) -> SelectMessage:
    sel = Expression(VariableRef("quantity"), FunctionAnnotation("number"))
    msg = SelectMessage([sel], {})
    var_comment: list[str | None] = []
    for item in el:
        if isinstance(item, etree._Comment):
            var_comment.append(item.text)
        elif item.tag == "item":
            key = item.attrib.get("quantity", None)
            if key not in plural_categories:
                raise ValueError(f"Invalid quantity for {name} plurals item: {key}")
            if var_comment:
                add_comment(
                    (f"{key}: {c}" for c in var_comment if c)
                    if msg.variants
                    else var_comment
                )
                var_comment.clear()
            msg.variants[(CatchallKey(key) if key == "other" else key,)] = list(
                parse_pattern(item)
            )
        else:
            cs = etree.tostring(item, encoding="unicode")
            raise ValueError(f"Unsupported {name} plurals child: {cs}")
        if item.tail and not item.tail.isspace():
            raise ValueError(f"Unexpected text in {name} plurals: {item.tail}")
    return msg


resource_ref = compile(r"@(?:\w+:)?\w+/\w+|\?(?:\w+:)?(\w+/)?\w+")


def parse_pattern(el: etree._Element) -> Iterator[str | Expression | Markup]:
    children = list(el)
    if not children or all(isinstance(child, etree._Entity) for child in children):
        text = el.text or ""
        if not children and resource_ref.fullmatch(text):
            # https://developer.android.com/guide/topics/resources/providing-resources#ResourcesFromXml
            yield Expression(VariableRef(text), FunctionAnnotation("reference"))
            return
        entities: list[Expression] = []
        for ent in cast(list[etree._Entity], children):
            # Spaces need to be collapsed while accounting for entities,
            # so temporarily replace each with a NUL character,
            # which is unrepresentable in XML.
            entities.append(
                Expression(VariableRef(ent.name), FunctionAnnotation("entity"))
            )
            text += "\0" + (ent.tail or "")
        if text:
            text = collapse_spaces(text)
            yield from parse_inline(text, entities)
    else:
        # Contains HTML elements, so pass through contents without escaping
        if el.text:
            yield el.text
        for child in children:
            yield from parse_element(child)


def parse_element(el: etree._Element) -> Iterator[str | Expression | Markup]:
    if isinstance(el, etree._Entity):
        yield Expression(VariableRef(el.name), FunctionAnnotation("entity"))
    else:
        yield Markup(kind="open", name=el.tag, options=dict(el.attrib))
        if el.text:
            yield el.text
        for child in el:
            yield from parse_element(child)
        yield Markup(kind="close", name=el.tag)
    if el.tail:
        yield el.tail


quotes_re = compile(r'(?<!\\)"(.*?)(?<!\\)"', flags=DOTALL)


def collapse_spaces(src: str) -> str:
    """
    Outside "double quoted" parts, collapse all whitespace to one space.
    """
    res = ""
    pos = 0
    for m in quotes_re.finditer(src):
        res += sub(r"\s+", " ", src[pos : m.start()]) + m[1]
        pos = m.end()
    if pos < len(src):
        res += sub(r"\s+", " ", src[pos:])
    return res


inline_re = compile(
    r"(\0)|"
    r"""\\([@?nt'"])|"""
    r"\\u([0-9]{4})|"
    r"(<[^%>]+>)|"
    r"(%(?:[1-9]\$)?[-#+ 0,(]?[0-9.]*([a-su-zA-SU-Z%]|[tT][a-zA-Z]))"
)


def parse_inline(src: str, entities: list[Expression]) -> Iterator[str | Expression]:
    cur = ""
    pos = 0
    for m in inline_re.finditer(src):
        cur += src[pos : m.start()]
        if m[1]:
            # XML entity
            if cur:
                yield cur
                cur = ""
            yield entities.pop(0)
        elif m[2]:
            # Special character
            c = m[2]
            cur += "\n" if c == "n" else "\t" if c == "t" else c
        elif m[3]:
            # Unicode escape
            cur += chr(int(m[3]))
        elif m[4]:
            # Escaped HTML element, e.g. &lt;b>
            # HTML elements containing internal % formatting are not wrapped as literals
            if cur:
                yield cur
                cur = ""
            yield Expression(m[4], FunctionAnnotation("html"))
        elif m[5]:
            conversion = m[6]
            if conversion == "%":
                # Literal %
                cur += "%"
            else:
                # Placeholder
                if cur:
                    yield cur
                    cur = ""
                exp = Expression(VariableRef(m[5]))
                if conversion in ("b", "B"):
                    exp.annotation = FunctionAnnotation("boolean")
                elif conversion in ("c", "C", "s", "S"):
                    exp.annotation = FunctionAnnotation("string")
                elif conversion in ("d", "h", "H", "o", "x", "X"):
                    exp.annotation = FunctionAnnotation("integer")
                elif conversion in ("a", "A", "e", "E", "f", "g", "G"):
                    exp.annotation = FunctionAnnotation("number")
                elif conversion[0] in ("t", "T"):
                    exp.annotation = FunctionAnnotation("datetime")
                yield exp
        pos = m.end()
    if cur or pos < len(src):
        yield cur + src[pos:]
