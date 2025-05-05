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

from os.path import join
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from moz.l10n.bin.lint import lint

from .test_walk_files import test_data_files

# /python/
root = Path(__file__).parent.parent
test_data_dir = join(root, "tests", "formats", "data")

try:
    from moz.l10n.formats.xliff import xliff_parse

    assert xliff_parse
    has_xml = True
except ImportError:
    has_xml = False


class TestLintCommand(TestCase):
    def test_directory(self):
        with self.assertLogs("moz.l10n.bin.lint", level="INFO") as logs:
            assert lint([test_data_dir]) == 1
        logs.output.sort()
        assert (
            logs.output
            == [
                "INFO:moz.l10n.bin.lint:ok accounts.dtd",
                "INFO:moz.l10n.bin.lint:ok angular.xliff",
                "INFO:moz.l10n.bin.lint:ok bug121341.properties",
                "INFO:moz.l10n.bin.lint:ok defines.inc",
                "INFO:moz.l10n.bin.lint:ok demo.ftl",
                "INFO:moz.l10n.bin.lint:ok foo.po",
                "INFO:moz.l10n.bin.lint:ok hello.xliff",
                "INFO:moz.l10n.bin.lint:ok icu-docs.xliff",
                "INFO:moz.l10n.bin.lint:ok messages.json",
                "INFO:moz.l10n.bin.lint:ok plain.json",
                "INFO:moz.l10n.bin.lint:ok strings.xml",
                "INFO:moz.l10n.bin.lint:ok test.properties",
                "INFO:moz.l10n.bin.lint:ok xcode.xliff",
                "WARNING:moz.l10n.bin.lint:unsupported mf2-message-schema.json",
            ]
            if has_xml
            else [
                "INFO:moz.l10n.bin.lint:ok accounts.dtd",
                "INFO:moz.l10n.bin.lint:ok bug121341.properties",
                "INFO:moz.l10n.bin.lint:ok defines.inc",
                "INFO:moz.l10n.bin.lint:ok demo.ftl",
                "INFO:moz.l10n.bin.lint:ok foo.po",
                "INFO:moz.l10n.bin.lint:ok messages.json",
                "INFO:moz.l10n.bin.lint:ok plain.json",
                "INFO:moz.l10n.bin.lint:ok test.properties",
                "WARNING:moz.l10n.bin.lint:unsupported angular.xliff",
                "WARNING:moz.l10n.bin.lint:unsupported hello.xliff",
                "WARNING:moz.l10n.bin.lint:unsupported icu-docs.xliff",
                "WARNING:moz.l10n.bin.lint:unsupported mf2-message-schema.json",
                "WARNING:moz.l10n.bin.lint:unsupported strings.xml",
                "WARNING:moz.l10n.bin.lint:unsupported xcode.xliff",
            ]
        )

    def test_files(self):
        unsupported_files = (
            {"mf2-message-schema.json"}
            if has_xml
            else {
                "angular.xliff",
                "hello.xliff",
                "icu-docs.xliff",
                "mf2-message-schema.json",
                "strings.xml",
                "xcode.xliff",
            }
        )
        for file in test_data_files:
            path = join(test_data_dir, file)
            exp = 1 if file in unsupported_files else 0
            assert lint([path]) == exp

    def test_parse_error(self):
        with TemporaryDirectory() as root:
            json_path = join(root, "one.json")
            with open(json_path, "x") as file:
                file.write('{"key":{"message":"Missing $VAR$"}}\n')
            ftl_path = join(root, "two.ftl")
            with open(ftl_path, "x") as file:
                file.write("key = broken { value\n")
            with self.assertLogs("moz.l10n.bin.lint", level="INFO") as logs:
                assert lint([json_path, ftl_path]) == 1
                assert logs.output == [
                    f"WARNING:moz.l10n.bin.lint:FAIL {join(root, 'one.json')} - Missing placeholders entry for var",
                    f'WARNING:moz.l10n.bin.lint:FAIL {join(root, "two.ftl")} - Expected token: "{"}"}"',
                ]
