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

from collections.abc import Iterator
from json import loads
from typing import Any

from ..resource import Entry, Resource, Section


def plain_parse(source: str | bytes) -> Resource[str, None]:
    """
    Parse a JSON file into a message resource.

    The input is expected to be a nested object with string values at leaf nodes.
    """
    json: dict[str, dict[str, Any]] = loads(source)
    if not isinstance(json, dict):
        raise ValueError(f"Unexpected root value: {json}")
    return Resource([Section([], [e for e in plain_object([], json)])])


def plain_object(path: list[str], obj: dict[str, Any]) -> Iterator[Entry[str, None]]:
    for k, value in obj.items():
        key = path + [k]
        if isinstance(value, str):
            yield Entry(key, value)
        elif isinstance(value, dict):
            yield from plain_object(key, value)
        else:
            raise ValueError(f"Unexpected value at {key}: {value}")
