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

from importlib_resources import files
from unittest import TestCase

from moz.l10n.resource import Format, detect_format


class TestDetectFormat(TestCase):
    def test_data_files(self):
        data = {
            "accounts.dtd": Format.dtd,
            "angular.xliff": Format.xliff,
            "bug121341.properties": Format.properties,
            "defines.inc": Format.inc,
            "demo.ftl": Format.fluent,
            "foo.po": Format.po,
            "hello.xliff": Format.xliff,
            "icu-docs.xliff": Format.xliff,
            "messages.json": Format.webext,
            "strings.xml": Format.android,
            "test.properties": Format.properties,
            "xcode.xliff": Format.xliff,
        }
        for file, exp_format in data.items():
            source = files("tests.resource.data").joinpath(file).read_bytes()
            assert detect_format(file, source) == exp_format

    def test_xliff_source(self):
        for file in ("angular.xliff", "hello.xliff", "icu-docs.xliff", "xcode.xliff"):
            source = files("tests.resource.data").joinpath(file).read_bytes()
            assert detect_format(None, source) == Format.xliff
