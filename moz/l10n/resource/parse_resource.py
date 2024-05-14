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

from ..message import Message
from .android.parse import android_parse
from .data import Resource
from .dtd.parse import dtd_parse
from .fluent.parse import fluent_parse
from .format import Format, detect_format
from .inc.parse import inc_parse
from .ini.parse import ini_parse
from .plain_json.parse import plain_json_parse
from .po.parse import po_parse
from .properties.parse import properties_parse
from .webext.parse import webext_parse
from .xliff.parse import xliff_parse


def parse_resource(
    input: Format | str | None, source: str | bytes | None = None
) -> Resource[Message, str]:
    """
    Parse a Resource from its string representation.

    The first argument may be an explicit Format,
    the file path as a string, or None.
    For the latter two types,
    an attempt is made to detect the appropriate format.

    If the first argument is a string path,
    the `source` argument is optional,
    as the file will be opened and read.
    """
    if source is None:
        if not isinstance(input, str):
            raise TypeError("Source is required if type is not a string path")
        with open(input, mode="rb") as file:
            source = file.read()
    match input if isinstance(input, Format) else detect_format(input, source):
        case Format.android:
            return android_parse(source)
        case Format.dtd:
            return dtd_parse(source)
        case Format.fluent:
            return fluent_parse(source)
        case Format.inc:
            return inc_parse(source)
        case Format.ini:
            return ini_parse(source)
        case Format.plain_json:
            return plain_json_parse(source)
        case Format.po:
            return po_parse(source)
        case Format.properties:
            return properties_parse(source)
        case Format.webext:
            return webext_parse(source)
        case Format.xliff:
            return xliff_parse(source)
        case _:
            raise ValueError(f"Unsupported resource format: {input}")
