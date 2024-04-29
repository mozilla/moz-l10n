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

from moz.l10n.message import Message

from .android.serialize import android_serialize
from .data import Resource
from .dtd.serialize import dtd_serialize
from .fluent.serialize import fluent_serialize
from .format import Format
from .inc.serialize import inc_serialize
from .ini.serialize import ini_serialize
from .plain_json.serialize import plain_json_serialize
from .po.serialize import po_serialize
from .properties.serialize import properties_serialize
from .webext.serialize import webext_serialize
from .xliff.serialize import xliff_serialize


def serialize_resource(
    resource: Resource[str, str] | Resource[Message, str],
    format: Format | None = None,
    trim_comments: bool = False,
) -> Iterator[str]:
    """
    Serialize a Resource as its string representation.
    """
    match format or resource.format:
        case Format.android:
            return android_serialize(resource, trim_comments=trim_comments)
        case Format.dtd:
            return dtd_serialize(resource, trim_comments=trim_comments)
        case Format.fluent:
            return fluent_serialize(resource, trim_comments=trim_comments)
        case Format.inc:
            return inc_serialize(resource, trim_comments=trim_comments)
        case Format.ini:
            return ini_serialize(resource, trim_comments=trim_comments)
        case Format.plain_json:
            return plain_json_serialize(resource, trim_comments=trim_comments)
        case Format.po:
            return po_serialize(resource, trim_comments=trim_comments)
        case Format.properties:
            return properties_serialize(resource, trim_comments=trim_comments)
        case Format.webext:
            return webext_serialize(resource, trim_comments=trim_comments)
        case Format.xliff:
            return xliff_serialize(resource, trim_comments=trim_comments)
        case _:
            raise ValueError(
                f"Unsupported resource format: {format or resource.format}"
            )
