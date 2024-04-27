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

from .android.parse import android_parse
from .detect_format import Format, detect_format
from .dtd.parse import dtd_parse
from .fluent.parse import fluent_parse, fluent_parse_message
from .inc.parse import inc_parse
from .ini.parse import ini_parse
from .message import Message
from .plain.parse import plain_parse
from .po.parse import po_parse
from .properties.parse import properties_parse
from .resource import Resource
from .webext.parse import webext_parse
from .xliff.parse import xliff_parse


def parse_resource(
    type: Format | str | None, source: str | bytes
) -> Resource[str, str] | Resource[Message, str]:
    """
    Parse a Resource from its string representation.

    The first argument may be an explicit Format,
    the filename as a string, or None.
    For the latter two types,
    an attempt is made to detect the appropriate format.
    """
    match type if isinstance(type, Format) else detect_format(type, source):
        case Format.android:
            return android_parse(source)
        case Format.dtd:
            return dtd_parse(source)
        case Format.fluent:
            return fluent_parse(source, parse_message=fluent_parse_message)
        case Format.inc:
            return inc_parse(source)
        case Format.ini:
            return ini_parse(source)
        case Format.plain:
            return plain_parse(source)
        case Format.po:
            return po_parse(source)
        case Format.properties:
            return properties_parse(source)
        case Format.webext:
            return webext_parse(source)
        case Format.xliff:
            return xliff_parse(source)
        case _:
            raise ValueError(f"Unsupported resource format: {type}")
