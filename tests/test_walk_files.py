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

from os import getcwd, sep
from os.path import join
from tempfile import TemporaryDirectory
from unittest import TestCase

from moz.l10n.util import walk_files

test_data_files = (
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


class TestWalkFiles(TestCase):
    def test_direct_children(self):
        root = join(getcwd(), "tests", "resource", "data")
        files = set(walk_files(root))
        assert files == {join(root, path) for path in test_data_files}

    def test_dirs(self):
        root = getcwd()
        files = set(walk_files(root, dirs=[f"tests{sep}resource{sep}data"]))
        assert files == {
            join(root, "tests", "resource", "data", path) for path in test_data_files
        }

    def test_l10nignore(self):
        root = getcwd()
        with TemporaryDirectory() as tmpdir:
            ignorepath = join(tmpdir, ".l10n-ignore")
            with open(ignorepath, mode="w") as file:
                file.write("__pycache__\n*.py\n")
            files = set(
                walk_files(
                    root, dirs=["src", f"tests{sep}resource"], ignorepath=ignorepath
                )
            )
            assert files == {
                join(root, "tests", "resource", "data", path)
                for path in test_data_files
            }
