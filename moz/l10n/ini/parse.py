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
from io import StringIO
from typing import Any, Generator, TextIO, cast, overload

from iniparse import ini  # type: ignore[import-untyped]

from ..resource import Comment, Entry, Resource, Section, V


@overload
def ini_parse(
    source: TextIO | str | bytes,
    parse_message: Callable[[str], str] | None = None,
) -> Resource[str, None]: ...


@overload
def ini_parse(
    source: TextIO | str | bytes,
    parse_message: Callable[[str], V],
) -> Resource[V, None]: ...


def ini_parse(
    source: TextIO | str | bytes,
    parse_message: Callable[[str], V] | None = None,
) -> Resource[V, None]:
    """
    Parse an .ini file into a message resource
    """
    if isinstance(source, str):
        file: TextIO = StringIO(source)
    elif isinstance(source, bytes):
        file = StringIO(source.decode())
    else:
        file = source
    cfg = ini.INIConfig(file, optionxformvalue=None)

    resource = Resource[V, None]([])
    section: Section[V, None] | None = None
    entry: Entry[V, None] | None = None
    comment = ""

    def add_comment(cl: str | None) -> None:
        nonlocal comment
        cv = cl[1:] if cl and cl.startswith(" ") else cl
        if cv:
            comment = f"{comment}\n{cv}" if comment else cv

    for line in ini_lines(cfg._data):
        if entry:
            if isinstance(line, ini.ContinuationLine):
                entry.value += "\n" + line.value
                continue
            elif isinstance(line, ini.EmptyLine):
                entry.value += cast(Any, "\n")
            else:
                value = cast(str, entry.value).rstrip("\n")
                entry.value = parse_message(value) if parse_message else cast(V, value)
                entry = None
        if isinstance(line, ini.SectionLine):
            add_comment(line.comment)
            section = Section([line.name], [], comment)
            comment = ""
            resource.sections.append(section)
        elif isinstance(line, ini.OptionLine):
            add_comment(line.comment)
            entry = Entry([line.name], line.value, comment)
            comment = ""
            if section:
                section.entries.append(entry)
            else:
                raise Exception(f"Unexpected value {line.name} before section header")
        elif isinstance(line, ini.CommentLine):
            add_comment(line.comment)
        elif isinstance(line, ini.EmptyLine):
            if comment:
                if section:
                    section.entries.append(Comment(comment))
                else:
                    resource.comment = (
                        f"{resource.comment}\n\n{comment}"
                        if resource.comment
                        else comment
                    )
                comment = ""
        else:
            raise Exception(f"Unexpected {line.__class__.__name__}: {line.__dict__}")
    if entry:
        value = cast(str, entry.value).rstrip("\n")
        entry.value = parse_message(value) if parse_message else cast(V, value)
    if comment:
        if section:
            section.entries.append(Comment(comment))
        else:
            resource.comment = (
                f"{resource.comment}\n\n{comment}" if resource.comment else comment
            )
    return resource


def ini_lines(data: ini.LineContainer) -> Generator[ini.LineType, None, None]:
    for line in data.contents:
        if isinstance(line, ini.LineContainer):
            yield from ini_lines(line)
        else:
            yield line
