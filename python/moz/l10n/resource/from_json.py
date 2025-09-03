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

from ..formats import Format
from ..message import entry_from_json
from ..model import Message, Metadata, Resource, Section


def resource_from_json(json: dict[str, Any]) -> Resource[Message]:
    """
    Marshal the JSON output of `moz.l10n.resource.to_json()`
    back into a parsed `moz.l10n.model.Resource`.

    May raise `MF2ValidationError`.
    """
    return Resource(
        format=Format[json["fmt"]] if "fmt" in json else None,
        meta=_meta(json),
        comment=json.get("#", ""),
        sections=[_section(s) for s in json["*"]],
    )


def _section(json: dict[str, Any]) -> Section[Message]:
    return Section(
        id=tuple(json.get("id", ())),
        meta=_meta(json),
        comment=json.get("#", ""),
        entries=[entry_from_json(key, e) for key, e in json["~"].items()],
    )


def _meta(json: dict[str, Any]) -> list[Metadata]:
    if "@" in json:
        return [Metadata(key, value) for key, value in json["@"]]
    return []
