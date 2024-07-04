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

# The core logic of the parser used here is taken from silme:
# https://github.com/mozilla/silme/blob/2f7af3dd87fff27a3c3650d442a065b5a290268e/lib/silme/format/dtd/parser.py

from __future__ import annotations

from collections.abc import Iterator
from re import DOTALL, MULTILINE, UNICODE, compile
from sys import maxsize
from typing import Any

from moz.l10n.message import Message, PatternMessage

from ..data import Comment, Entry, Resource, Section
from ..format import Format

name_start_char = (
    ":A-Z_a-z\xC0-\xD6\xD8-\xF6\xF8-\u02FF"
    "\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF"
    "\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD"
)
name_char = name_start_char + r"\-\.0-9" + "\xB7\u0300-\u036F\u203F-\u2040"
name = f"[{name_start_char}][{name_char}]*"
re_entity = compile(
    r"<!ENTITY\s+(" + name + r")\s+((?:\"[^\"]*\")|(?:'[^']*'))\s*>",
    DOTALL | UNICODE,
)

re_comment = compile(r"\<!\s*--(.*?)--\s*\>", MULTILINE | DOTALL)


def dtd_parse(source: str | bytes) -> Resource[Message, Any]:
    """
    Parse a .dtd file into a message resource.

    The parsed resource will not include any metadata.
    """
    entries: list[Entry[Message, Any] | Comment] = []
    resource = Resource(Format.dtd, [Section((), entries)])
    pos = 0
    at_newline = True
    comment: str = ""
    if not isinstance(source, str):
        source = source.decode()
    for match in re_comment.finditer(source):
        cstart = match.start(0)
        has_prev_entries = False
        for entry in dtd_iter(source, pos, endpos=cstart):
            if isinstance(entry, str):
                if entry and not entry.isspace():
                    raise ValueError(f"Unexpected content in DTD: {entry}")
                lines = entry.split("\n")
                if comment and len(lines) > 2:
                    if entries or resource.comment:
                        entries.append(Comment(comment))
                    else:
                        resource.comment = comment
                    comment = ""
                at_newline = len(lines) > 1
            else:
                if comment:
                    entry.comment = comment
                    comment = ""
                entries.append(entry)
                has_prev_entries = True
        nc = match.group(1).strip().replace("\r\n", "\n")
        comment = f"{comment}\n{nc}" if comment else nc
        if comment:
            if not at_newline and has_prev_entries:
                prev = entries[-1]
                pc = prev.comment
                prev.comment = f"{pc}\n{comment}" if pc else comment
                comment = ""
            if re_entity.search(comment):
                entries.append(Comment(comment))
                comment = ""
        pos = match.end(0)
    if len(source) > pos:
        for entry in dtd_iter(source, pos):
            if isinstance(entry, str):
                if entry and not entry.isspace():
                    raise ValueError(f"Unexpected content in DTD: {entry}")
            else:
                if comment:
                    entry.comment = comment
                    comment = ""
                entries.append(entry)
    if comment:
        entries.append(Comment(comment))
    return resource


def dtd_iter(
    text: str, pos: int, endpos: int = maxsize
) -> Iterator[str | Entry[Message, Any]]:
    for match in re_entity.finditer(text, pos, endpos):
        yield text[pos : match.start(0)]
        id, value = match.groups()
        yield Entry((id,), PatternMessage([value[1:-1]]))
        pos = match.end(0)
    yield text[pos:endpos]
