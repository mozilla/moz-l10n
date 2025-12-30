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

from importlib.resources import files

from moz.l10n.model import LinePos


def get_linepos(
    start: int,
    key: int | None = None,
    value: int | None = None,
    end: int | None = None,
) -> LinePos:
    if key is None:
        key = start
    if value is None:
        value = key
    if end is None:
        end = value + 1
    return LinePos(start, key, value, end)


def get_test_resource(filename: str) -> bytes:
    return files("tests.formats").joinpath("data").joinpath(filename).read_bytes()
