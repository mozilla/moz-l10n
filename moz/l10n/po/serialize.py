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

from typing import Iterator

from polib import POEntry, POFile

from ..resource import Entry, Resource
from .parse import PoMetadataType


def po_serialize(
    resource: Resource[tuple[str, ...], PoMetadataType],
    trim_comments: bool = False,
    wrapwidth: int = 78,
) -> Iterator[str]:
    """
    Serialize a resource as the contents of a .po file.

    Multi-part identifiers will be joined with `.` between each part.
    Section identifiers are serialized as message contexts.
    Comments and metadata on sections is not supported.

    Yields each entry and empty line separately.
    Re-parsing a serialized .properties file is not guaranteed to result in the same Resource,
    as the serialization may lose information about message identifiers.
    """

    pf = POFile(wrapwidth=wrapwidth)
    if not trim_comments:
        pf.header = resource.comment.rstrip() + "\n"
    pf.metadata = {m.key: str(m.value) for m in resource.meta}
    yield str(pf)

    for section in resource.sections:
        if section.comment:
            raise ValueError(f"Section comments are not supported: {section.id}")
        if section.meta:
            raise ValueError(f"Section metadata is not supported: {section.id}")
        context = ".".join(section.id) if section.id else None
        for entry in section.entries:
            if isinstance(entry, Entry):
                pe = POEntry(msgctxt=context, msgid=".".join(entry.id))
                if isinstance(entry.value, str):
                    pe.msgstr = entry.value
                elif isinstance(entry.value, tuple) and all(
                    isinstance(v, str) for v in entry.value
                ):
                    if len(entry.value) == 1:
                        pe.msgstr = entry.value[0]
                    else:
                        pe.msgstr_plural = {
                            idx: str for idx, str in enumerate(entry.value)
                        }
                else:
                    raise Exception(
                        f"Value for {entry.id} is not a string or tuple of strings: {entry.value}"
                    )
                if not trim_comments:
                    pe.tcomment = entry.comment.rstrip()
                for m in entry.meta:
                    if m.key == "plural":
                        pe.msgid_plural = str(m.value)
                    elif not trim_comments:
                        if m.key == "translator-comments":
                            cs = str(m.value).lstrip("\n").rstrip()
                            pe.tcomment = f"{pe.tcomment}\n{cs}" if pe.tcomment else cs
                        elif m.key == "extracted-comments":
                            pe.comment = str(m.value).lstrip("\n").rstrip()
                        elif m.key == "references":
                            if isinstance(m.value, (tuple, list)) and all(
                                isinstance(ref, tuple)
                                and isinstance(ref[0], str)
                                and isinstance(ref[1], (int, str))
                                for ref in m.value
                            ):
                                pe.occurrences = m.value  # type: ignore[assignment]
                            else:
                                raise ValueError(
                                    f"Unsupported references metadata for {entry.id}: {m.value}"
                                )
                        elif m.key == "flags":
                            pe.flags = (
                                [m.value]
                                if isinstance(m.value, str)
                                else [str(flag) for flag in m.value]
                            )
                        else:
                            raise ValueError(
                                f'Unsupported meta entry "{m.key}" for {entry.id}: {m.value}'
                            )
                yield "\n"
                yield pe.__unicode__(wrapwidth=wrapwidth)
            else:
                raise ValueError(
                    f"Standalone comments are not supported: {entry.comment}"
                )
