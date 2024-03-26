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

from collections.abc import Callable, Iterator
from re import search

from ..resource import Entry, M, Metadata, Resource, V


def ini_serialize(
    resource: Resource[V, M],
    serialize_message: Callable[[V], str] | None = None,
    serialize_metadata: Callable[[Metadata[M]], str | None] | None = None,
    trim_comments: bool = False,
) -> Iterator[str]:
    """
    Serialize a resource as the contents of an .ini file.

    Anonymous sections are not supported.
    Multi-part section and message identifiers will be joined with `.` between each part.

    For non-string message values, a `serialize_message` callable must be provided.
    If the resource includes any metadata, a `serialize_metadata` callable must be provided
    to map each field into a comment value, or to discard it by returning an empty value.

    Comment lines not starting with `#` will be separated from their `#` prefix with a space.

    Yields each entry, continuation line, comment, and empty line separately.
    Re-parsing a serialized .ini file is not guaranteed to result in the same Resource,
    as the serialization may lose information about metadata.
    """

    at_empty_line = True

    def comment(
        comment: str, meta: list[Metadata[M]] | None, standalone: bool
    ) -> Iterator[str]:
        nonlocal at_empty_line
        if trim_comments:
            return
        lines = comment.strip("\n").split("\n") if comment else []
        if meta:
            if not serialize_metadata:
                raise Exception("Metadata requires serialize_metadata parameter")
            for field in meta:
                meta_str = serialize_metadata(field)
                if meta_str:
                    lines += meta_str.strip("\n").split("\n")
        if lines:
            if standalone and not at_empty_line:
                yield "\n"
            for line in lines:
                if not line or line.isspace():
                    yield "#\n"
                else:
                    line = line.rstrip() + "\n"
                    yield f"#{line}" if line.startswith("#") else f"# {line}"
            if standalone:
                yield "\n"
                at_empty_line = True

    yield from comment(resource.comment, resource.meta, True)
    for section in resource.sections:
        if not section.id:
            raise ValueError("Anonymous sections are not supported")
        yield from comment(section.comment, section.meta, False)
        yield f"[{id_str(section.id)}]\n"
        at_empty_line = False
        for entry in section.entries:
            if isinstance(entry, Entry):
                yield from comment(entry.comment, entry.meta, False)
                source = (
                    serialize_message(entry.value) if serialize_message else entry.value
                )
                if not isinstance(source, str):
                    raise Exception(f"Source value for {entry.id} is not a string")
                lines = source.rstrip().splitlines()
                yield f"{id_str(entry.id)} = {lines.pop(0)}".rstrip() + "\n"
                for line in lines:
                    ls = line.rstrip()
                    yield f"  {ls}\n" if ls else "\n"
                at_empty_line = False
            else:
                yield from comment(entry.comment, None, True)


def id_str(id: list[str]) -> str:
    name = ".".join(id)
    if search(r"^\s|[\n:=[\]]|\s$", name):
        raise ValueError(f"Unsupported character in identifier: {id}")
    return name
