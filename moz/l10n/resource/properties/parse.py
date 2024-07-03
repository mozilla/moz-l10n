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

from collections.abc import Callable
from re import sub
from typing import Any

from translate.storage.properties import propfile

from moz.l10n.message import Message, PatternMessage

from ..data import Comment, Entry, Resource, Section
from ..format import Format


def parse_comment(lines: list[str]) -> str:
    return "\n".join(sub("^# ?", "", line) for line in lines if line.startswith("#"))


class propfile_shim(propfile):  # type: ignore[misc]
    def detect_encoding(
        self, text: str, default_encodings: list[str] | None = None
    ) -> tuple[str, str]:
        """
        Allow propfile().parse() to parse str inputs.
        """
        return (text, default_encodings[0] if default_encodings else "utf-8")


def properties_parse(
    source: bytes | str,
    encoding: str = "utf-8",
    parse_message: Callable[[str], Message] | None = None,
) -> Resource[Message, Any]:
    """
    Parse a .properties file into a message resource.

    By default, all messages are parsed as PatternMessage([str]).
    To customize that, define an appropriate `parse_message(str) -> Message`.

    The parsed resource will not include any metadata.
    """
    pf = propfile_shim(personality="java-utf8")
    if encoding != "utf-8":
        pf.default_encoding = encoding
    pf.parse(source if isinstance(source, str) else source.decode(encoding))
    entries: list[Entry[Message, Any] | Comment] = []
    resource = Resource(Format.properties, [Section((), entries)])
    for unit in pf.getunits():
        if unit.name or unit.value:
            entries.append(
                Entry(
                    id=(unit.name,),
                    value=(
                        parse_message(unit.source)
                        if parse_message
                        else PatternMessage([unit.source])
                    ),
                    comment=parse_comment(unit.comments),
                )
            )
        else:
            comment = parse_comment(unit.comments)
            if comment:
                if entries or resource.comment:
                    entries.append(Comment(comment))
                else:
                    resource.comment = comment
    return resource
