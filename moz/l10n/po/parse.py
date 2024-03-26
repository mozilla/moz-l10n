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

from collections import OrderedDict
from typing import cast

from polib import pofile

from ..resource import Entry, Metadata, Resource, Section

PoMetadataType = str | list[str] | list[tuple[str, str]]
"""
All resource-level metadata has `str` values matching the .po header fields.

Messages may include the following metadata:
- "translator-comments": `str`
- "extracted-comments": `str`
- "references": `list[tuple[str, str]]`
- "flags": `list[str]`
- "plural": `str`
"""


def po_parse(source: str) -> Resource[tuple[str, ...], PoMetadataType]:
    """
    Parse a .po or .pot file into a message resource
    """
    pf = pofile(source)
    res_comment = pf.header.lstrip("\n").rstrip()
    res_meta: list[Metadata[PoMetadataType]] = [
        Metadata(key, value.strip()) for key, value in pf.metadata.items()
    ]
    sections: dict[str | None, Section[tuple[str, ...], PoMetadataType]] = OrderedDict()
    for pe in pf:
        meta: list[Metadata[PoMetadataType]] = []
        if pe.tcomment:
            meta.append(Metadata("translator-comments", pe.tcomment))
        if pe.comment:
            meta.append(Metadata("extracted-comments", pe.comment))
        if pe.occurrences:
            meta.append(
                Metadata("references", cast(list[tuple[str, str]], pe.occurrences))
            )
        if pe.flags:
            meta.append(Metadata("flags", pe.flags))
        if pe.msgid_plural:
            meta.append(Metadata("plural", pe.msgid_plural))
        if pe.msgstr_plural:
            keys = list(pe.msgstr_plural)
            keys.sort()
            value = tuple(pe.msgstr_plural.get(idx, "") for idx in range(keys[-1] + 1))
        else:
            value = (pe.msgstr,)
        entry = Entry([pe.msgid], value, meta=meta)
        if pe.msgctxt in sections:
            sections[pe.msgctxt].entries.append(entry)
        else:
            sections[pe.msgctxt] = Section([pe.msgctxt] if pe.msgctxt else [], [entry])
    return Resource(list(sections.values()), res_comment, res_meta)
