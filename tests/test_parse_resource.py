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

from importlib.resources import files
from unittest import TestCase

from moz.l10n import Format, parse_resource
from moz.l10n.resource import Resource


def get_source(filename: str) -> bytes:
    return files("tests.data").joinpath(filename).read_bytes()


class TesteParseResource(TestCase):
    def test_named_files(self):
        data = (
            "accounts.dtd",
            "angular.xliff",
            "bug121341.properties",
            "defines.inc",
            "demo.ftl",
            "foo.po",
            "hello.xliff",
            "icu-docs.xliff",
            "messages.json",
            "strings.xml",
            "test.properties",
            "xcode.xliff",
        )
        for file in data:
            res = parse_resource(file, get_source(file))
            assert isinstance(res, Resource)

    def test_anon_files(self):
        data = {
            Format.android: ("messages.json",),
            Format.xliff: (
                "angular.xliff",
                "hello.xliff",
                "icu-docs.xliff",
                "xcode.xliff",
            ),
        }
        for format, values in data.items():
            for file in values:
                res = parse_resource(None, get_source(file))
                assert isinstance(res, Resource)

    def test_unknown_format(self):
        source = get_source("accounts.dtd")
        with self.assertRaises(ValueError):
            parse_resource(None, source)
