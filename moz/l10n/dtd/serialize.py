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
from re import UNICODE, compile

from ..resource import Entry, M, Metadata, Resource, V
from .parse import name, re_comment

re_name = compile(name, UNICODE)


def dtd_serialize(
    resource: Resource[V, M],
    serialize_message: Callable[[V], str] | None = None,
    serialize_metadata: Callable[[Metadata[M]], str | None] | None = None,
    trim_comments: bool = False,
) -> Iterator[str]:
    """
    Serialize a resource as the contents of a DTD file.

    Section identifiers will be prepended to their constituent message identifiers.
    Multi-part identifiers will be joined with `.` between each part.

    For non-string message values, a `serialize_message` callable must be provided.
    If the resource includes any metadata, a `serialize_metadata` callable must be provided
    to map each field into a comment value, or to discard it by returning an empty value.

    Yields each entity, comment, and empty line separately.
    Re-parsing a serialized DTD file is not guaranteed to result in the same Resource,
    as the serialization may lose information about message sections and metadata.
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
                raise ValueError("Metadata requires serialize_metadata parameter")
            for field in meta:
                meta_str = serialize_metadata(field)
                if meta_str:
                    lines += meta_str.strip("\n").split("\n")
        if lines:
            if standalone and not at_empty_line:
                yield "\n"
            # Comments can't include --, so add a zero width space between and after dashes beyond the first
            lines = [line.rstrip().replace("--", "-\u200b-\u200b") for line in lines]
            cstr = "<!--" if not lines[0] or lines[0].startswith(" ") else "<!-- "
            cstr += lines[0]
            for line in lines[1:]:
                cstr += "\n"
                if line and not line.isspace():
                    if not line.startswith(" "):
                        cstr += "     "
                    cstr += line
            yield cstr + " -->\n"
            if standalone:
                yield "\n"
                at_empty_line = True

    yield from comment(resource.comment, resource.meta, True)
    for section in resource.sections:
        yield from comment(section.comment, section.meta, True)
        id_prefix = ".".join(section.id) + "." if section.id else ""
        for entry in section.entries:
            if isinstance(entry, Entry):
                yield from comment(entry.comment, entry.meta, False)
                name = id_prefix + ".".join(entry.id)
                if not re_name.fullmatch(name):
                    raise ValueError(f"Unsupported DTD name: {name}")
                value = (
                    serialize_message(entry.value) if serialize_message else entry.value
                )
                if not isinstance(value, str):
                    raise ValueError(f"Source value for {name} is not a string")

                if '"' in value and "'" not in value:
                    quoted = f"'{value}'"
                else:
                    quoted = value.replace('"', "&quot;")
                    quoted = f'"{quoted}"'
                quoted = re_comment.sub("", quoted)

                yield f"<!ENTITY {name} {quoted}>\n"
                at_empty_line = False
            else:
                yield from comment(entry.comment, None, True)
