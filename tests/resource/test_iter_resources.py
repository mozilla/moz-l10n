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

from os import getcwd, sep
from os.path import join, splitext
from tempfile import TemporaryDirectory
from unittest import TestCase

from moz.l10n.resource import iter_resources
from moz.l10n.resource.data import Resource

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


class TestIterResources(TestCase):
    def test_direct_children(self):
        root = join(getcwd(), "tests", "resource", "data")
        resources = list(iter_resources(root))
        assert {x[0] for x in resources} == {
            join(root, path) for path in test_data_files
        }
        assert all(isinstance(x[1], Resource) for x in resources)

    def test_dirs(self):
        root = getcwd()
        resources = list(iter_resources(root, dirs=[f"tests{sep}resource{sep}data"]))
        assert {x[0] for x in resources} == {
            join(root, "tests", "resource", "data", path) for path in test_data_files
        }
        assert all(isinstance(x[1], Resource) for x in resources)

    def test_not_localizable(self):
        py_count = 0
        res_count = 0
        for path, res in iter_resources(getcwd(), dirs=["src", f"tests{sep}resource"]):
            if splitext(path)[1] in (".py", ".pyc"):
                assert res is None
                py_count += 1
            else:
                assert isinstance(res, Resource)
                res_count += 1
        assert py_count >= 10
        assert res_count >= 10

    def test_l10nignore(self):
        root = getcwd()
        with TemporaryDirectory() as tmpdir:
            ignorepath = join(tmpdir, ".l10n-ignore")
            with open(ignorepath, mode="w") as file:
                file.write("__pycache__\n*.py\n")
            resources = list(
                iter_resources(
                    root, dirs=["src", f"tests{sep}resource"], ignorepath=ignorepath
                )
            )
            assert {x[0] for x in resources} == {
                join(root, "tests", "resource", "data", path)
                for path in test_data_files
            }
            assert all(isinstance(x[1], Resource) for x in resources)
