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

from importlib.util import find_spec
from importlib_resources import files
from unittest import TestCase, skipIf

from moz.l10n.formats import Format, detect_format

no_xml = find_spec("lxml") is None


class TestDetectFormat(TestCase):
    def test_common_data_files(self):
        data = {
            "accounts.dtd": Format.dtd,
            "bug121341.properties": Format.properties,
            "defines.inc": Format.inc,
            "demo.ftl": Format.fluent,
            "foo.po": Format.po,
            "messages.json": Format.webext,
            "test.properties": Format.properties,
        }
        for file, exp_format in data.items():
            source = files("tests.resource.data").joinpath(file).read_bytes()
            assert detect_format(file, source) == exp_format

    @skipIf(no_xml, "Requires [xml] extra")
    def test_xml_data_files(self):
        data = {
            "angular.xliff": Format.xliff,
            "hello.xliff": Format.xliff,
            "icu-docs.xliff": Format.xliff,
            "strings.xml": Format.android,
            "xcode.xliff": Format.xliff,
        }
        for file, exp_format in data.items():
            source = files("tests.resource.data").joinpath(file).read_bytes()
            assert detect_format(file, source) == exp_format

    @skipIf(no_xml, "Requires [xml] extra")
    def test_xliff_source(self):
        for file in ("angular.xliff", "hello.xliff", "icu-docs.xliff", "xcode.xliff"):
            source = files("tests.resource.data").joinpath(file).read_bytes()
            assert detect_format(None, source) == Format.xliff
