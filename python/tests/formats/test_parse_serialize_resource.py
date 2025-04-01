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

from moz.l10n.formats import Format, UnsupportedFormat
from moz.l10n.model import Resource
from moz.l10n.resource import (
    parse_resource,
    serialize_resource,
)

no_xml = find_spec("lxml") is None


def get_source(filename: str) -> bytes:
    return files("tests.formats.data").joinpath(filename).read_bytes()


class TesteParseResource(TestCase):
    def test_named_common_files(self):
        data = (
            "accounts.dtd",
            "bug121341.properties",
            "defines.inc",
            "demo.ftl",
            "foo.po",
            "messages.json",
            "test.properties",
        )
        for file in data:
            res = parse_resource(file, get_source(file))
            assert isinstance(res, Resource)
            assert all(isinstance(s, str) for s in serialize_resource(res))
            assert all(
                isinstance(s, str) for s in serialize_resource(res, trim_comments=True)
            )

    @skipIf(no_xml, "Requires [xml] extra")
    def test_named_xml_files(self):
        data = (
            "angular.xliff",
            "hello.xliff",
            "icu-docs.xliff",
            "strings.xml",
            "xcode.xliff",
        )
        for file in data:
            res = parse_resource(file, get_source(file))
            assert isinstance(res, Resource)
            assert all(isinstance(s, str) for s in serialize_resource(res))
            assert all(
                isinstance(s, str) for s in serialize_resource(res, trim_comments=True)
            )

    @skipIf(no_xml, "Requires [xml] extra")
    def test_parse_anon_files(self):
        data = {
            Format.android: ("strings.xml",),
            Format.webext: ("messages.json",),
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
                assert res.format == format

    def test_parse_unknown_format(self):
        source = get_source("accounts.dtd")
        with self.assertRaises(UnsupportedFormat):
            parse_resource(None, source)

    def test_serialize_unsupported_format(self):
        source = get_source("foo.po")
        res = parse_resource(Format.po, source)
        with self.assertRaises(ValueError):
            assert all(
                isinstance(s, str) for s in serialize_resource(res, Format.fluent)
            )
