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

from collections.abc import Callable
from re import sub
from typing import cast, overload

from translate.storage.properties import propfile

from ..data import Comment, Entry, Resource, Section, V
from ..format import Format


def parse_comment(lines: list[str]) -> str:
    return "\n".join(sub("^# ?", "", line) for line in lines if line.startswith("#"))


class propfile_shim(propfile):  # type: ignore[misc]
    def detect_encoding(
        self, text: bytes | str, default_encodings: list[str] | None = None
    ) -> tuple[str, str]:
        """
        Allow propfile().parse() to parse str inputs.
        """
        if isinstance(text, str):
            return (text, default_encodings[0] if default_encodings else "utf-8")
        else:
            return cast(
                tuple[str, str], super().detect_encoding(text, default_encodings)
            )


@overload
def properties_parse(
    source: bytes | str,
    encoding: str = "utf-8",
    parse_message: Callable[[str], str] | None = None,
) -> Resource[str, str]: ...


@overload
def properties_parse(
    source: bytes | str,
    encoding: str = "utf-8",
    parse_message: Callable[[str], V] | None = None,
) -> Resource[V, str]: ...


def properties_parse(
    source: bytes | str,
    encoding: str = "utf-8",
    parse_message: Callable[[str], V] | None = None,
) -> Resource[V, str]:
    """
    Parse a .properties file into a message resource.

    The parsed resource will not include any metadata.
    """
    pf = propfile_shim(personality="java-utf8")
    if encoding != "utf-8":
        pf.default_encoding = encoding
    pf.parse(source)
    entries: list[Entry[V, str] | Comment] = []
    resource = Resource(Format.properties, [Section([], entries)])
    for unit in pf.getunits():
        if unit.name or unit.value:
            entries.append(
                Entry(
                    id=[unit.name],
                    value=parse_message(unit.source) if parse_message else unit.source,
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
