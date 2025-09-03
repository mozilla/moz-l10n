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

from typing import Any

from ..message import entry_to_json
from ..model import Entry, Message, Resource, Section


def resource_to_json(res: Resource[Message]) -> dict[str, Any]:
    """
    Represent the localizable parts of a Resource as a JSON-serializable value.

    Standalone comments and sections without

    The JSON Schema of the output is provided as [schema.json](./schema.json).
    """
    json: dict[str, Any] = {}
    if res.format is not None:
        json["fmt"] = res.format.name
    if res.meta:
        json["@"] = list([m.key, m.value] for m in res.meta)
    if res.comment:
        json["#"] = res.comment
    json_sections = (_section(section) for section in res.sections)
    json["*"] = list(s for s in json_sections if s is not None)
    return json


def _section(section: Section[Message]) -> dict[str, Any] | None:
    json: dict[str, Any] = {}
    if section.id:
        json["id"] = list(section.id)
    if section.meta:
        json["@"] = list([m.key, m.value] for m in section.meta)
    if section.comment:
        json["#"] = section.comment
    json["~"] = dict(
        entry_to_json(entry) for entry in section.entries if isinstance(entry, Entry)
    )
    return json if json["~"] else None
