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

from collections import defaultdict
from collections.abc import Iterator
from json import dumps
from typing import Any

from moz.l10n.message import Message, PatternMessage

from ..data import Entry, Metadata, Resource


def plain_json_serialize(
    resource: Resource[str, Any] | Resource[Message, Any],
    trim_comments: bool = False,
) -> Iterator[str]:
    """
    Serialize a resource as a nested JSON object.

    Comments and metadata are not supported.

    Yields the entire JSON result as a single string.
    """

    def check(comment: str | None, meta: list[Metadata[None]] | None) -> None:
        if comment and not trim_comments:
            raise ValueError("Resource and section comments are not supported")
        if meta:
            raise ValueError("Metadata is not supported")

    def ddict() -> dict[str, Any]:
        return defaultdict(ddict)

    check(resource.comment, resource.meta)
    root = ddict()
    for section in resource.sections:
        check(section.comment, section.meta)
        section_parent = root
        for part in section.id:
            section_parent = section_parent[part]
        for entry in section.entries:
            if isinstance(entry, Entry):
                check(entry.comment, entry.meta)
                if not entry.id:
                    raise ValueError(f"Unsupported empty identifier in {section.id}")
                msg = entry.value
                if isinstance(msg, str):
                    value = msg
                elif (
                    isinstance(msg, PatternMessage)
                    and not msg.declarations
                    and len(msg.pattern) == 1
                    and isinstance(msg.pattern[0], str)
                ):
                    value = msg.pattern[0]
                else:
                    raise ValueError(
                        f"Unsupported message for {section.id + entry.id}: {msg}"
                    )
                parent = section_parent
                for part in entry.id[:-1]:
                    parent = parent[part]
                parent[entry.id[-1]] = value
            else:
                check(entry.comment, None)
    yield dumps(root, indent=2)
    yield "\n"
