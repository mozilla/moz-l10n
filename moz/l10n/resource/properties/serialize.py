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
from typing import Literal

from translate.storage.properties import propunit

from ..data import Entry, M, Metadata, Resource, V


def properties_serialize(
    resource: Resource[V, M],
    encoding: Literal["iso-8859-1", "utf-8", "utf-16"] = "utf-8",
    serialize_message: Callable[[V], str] | None = None,
    serialize_metadata: Callable[[Metadata[M]], str | None] | None = None,
    trim_comments: bool = False,
) -> Iterator[str]:
    """
    Serialize a resource as the contents of a .properties file.

    Section identifiers will be prepended to their constituent message identifiers.
    Multi-part message identifiers will be joined with `.` between each part.

    For non-string message values, a `serialize_message` callable must be provided.
    If the resource includes any metadata, a `serialize_metadata` callable must be provided
    to map each field into a comment value, or to discard it by returning an empty value.

    Comment lines not starting with `#` will be prefixed with `# `.

    Yields each entry, comment, and empty line separately.
    Re-parsing a serialized .properties file is not guaranteed to result in the same Resource,
    as the serialization may lose information about message sections and metadata.
    """

    personality = "java-utf8" if encoding == "utf-8" or encoding == "utf-16" else "java"
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
                    yield line if line.startswith("#") else f"# {line}"
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
                unit = propunit(personality=personality)
                unit.out_delimiter_wrappers = " "
                unit.name = id_prefix + ".".join(entry.id)
                source = (
                    serialize_message(entry.value) if serialize_message else entry.value
                )
                if not isinstance(source, str):
                    raise Exception(f"Source value for {unit.name} is not a string")
                unit.source = source
                if unit.value[0:1].isspace():
                    unit.value = "\\" + unit.value
                if unit.value.endswith(" ") and not unit.value.endswith("\\ "):
                    unit.value = unit.value[:-1] + "\\u0020"
                yield unit.getoutput()
                at_empty_line = False
            else:
                yield from comment(entry.comment, None, True)
