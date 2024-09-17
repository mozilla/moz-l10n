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

from os import mkdir
from os.path import join, normpath
from tempfile import TemporaryDirectory
from typing import Dict, Union
from unittest import TestCase

from moz.l10n.paths import L10nDiscoverPaths, MissingSourceDirectoryError

Tree = Dict[str, Union[str, "Tree"]]


def build_file_tree(root: str, tree: Tree) -> None:
    for name, value in tree.items():
        path = join(root, name)
        if isinstance(value, str):
            with open(path, "x") as file:
                if value:
                    file.write(value)
        else:
            mkdir(path)
            build_file_tree(path, value)


class TestL10nDiscover(TestCase):
    def test_not_found(self):
        tree: Tree = {
            "one.pot": "",
            "two": {"a.ftl": "", "b.pot": ""},
            "three": {"c": "", "d": {"e": ""}, "f": {"g.ftl": ""}},
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)
            with self.assertRaises(MissingSourceDirectoryError):
                L10nDiscoverPaths(root)
            paths = L10nDiscoverPaths(
                root, ref_root=root, force_paths=[join(root, "extra.ftl")]
            )
            paths.base = join(root, "base")
        assert paths.ref_root == root
        assert paths.target("nonesuch.ftl") == (None, ())
        assert paths.target("extra.ftl") == (
            join(root, "base", "{locale}", "extra.ftl"),
            (),
        )

    def test_ref_only(self):
        tree: Tree = {
            "en": {
                "one.pot": "",
                "two": {"a.ftl": "", "b.pot": ""},
                "three": {"c": "", "d": {"e": ""}, "f": {"g.ftl": ""}},
            },
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)
            paths = L10nDiscoverPaths(root)

        assert paths.ref_root == join(root, "en")
        assert paths.base is None
        assert paths.locales is None
        with self.assertRaises(ValueError):
            paths.all()
        with self.assertRaises(ValueError):
            paths.target("one.pot")
        with self.assertRaises(ValueError):
            paths.format_target_path("one.pot", "xx")

        paths.base = join(root, "target")
        expected = {
            (
                join(root, "en", normpath(ref)),
                join(root, "target", "{locale}", normpath(tgt)),
            ): None
            for ref, tgt in {
                "one.pot": "one.po",
                "three/c": "three/c",
                "three/d/e": "three/d/e",
                "three/f/g.ftl": "three/f/g.ftl",
                "two/a.ftl": "two/a.ftl",
                "two/b.pot": "two/b.po",
            }.items()
        }
        assert paths.all() == expected
        for ref, tgt in expected:
            assert paths.target(ref) == (tgt, ())

    def test_ref_priorities(self):
        with TemporaryDirectory() as root:
            build_file_tree(root, {"en_US": {"a.ftl": ""}})
            assert L10nDiscoverPaths(root).ref_root == join(root, "en_US")

            build_file_tree(root, {"en": {"a.json": ""}})
            assert L10nDiscoverPaths(root).ref_root == join(root, "en_US")

            build_file_tree(join(root, "en"), {"a.pot": ""})
            assert L10nDiscoverPaths(root).ref_root == join(root, "en")

            build_file_tree(root, {"foo": {"en-US": {"bar": {"a.pot": ""}}}})
            assert L10nDiscoverPaths(root).ref_root == join(root, "foo", "en-US")

    def test_locales(self):
        tree: Tree = {
            "source": {
                "en": {"a.ftl": "", "b.ftl": "", "c.pot": ""},
                "en-US": {"d.ftl": "", "e.ftl": "", "f.ftl": ""},
            },
            "ignore": {"aa": {}, "bb": {}, "cc": {}, "dd": {}},
            "target": {
                "ignore": {"a.ftl": "", "b.ftl": ""},
                "zz": {"a.ftl": "", "b.ftl": ""},
                "yy_Latn": {"a.ftl": "", "b.ftl": ""},
            },
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)
            paths = L10nDiscoverPaths(root)

            assert paths.ref_root == join(root, "source", "en")
            assert paths.base == join(root, "target")
            assert paths.locales == ["yy-Latn", "zz"]
            assert paths.all() == {
                (
                    join(paths.ref_root, "a.ftl"),
                    join(paths.base, "{locale}", "a.ftl"),
                ): paths.locales,
                (
                    join(paths.ref_root, "b.ftl"),
                    join(paths.base, "{locale}", "b.ftl"),
                ): paths.locales,
                (
                    join(paths.ref_root, "c.pot"),
                    join(paths.base, "{locale}", "c.po"),
                ): paths.locales,
            }
            assert paths.target(join(paths.ref_root, "c.pot")) == paths.target("c.pot")
            assert paths.target("a.ftl") == (
                join(paths.base, "{locale}", "a.ftl"),
                paths.locales,
            )
            assert paths.target("c.pot") == (
                join(paths.base, "{locale}", "c.po"),
                paths.locales,
            )
            assert paths.target(join(root, "source", "en-US", "a.ftl")) == (None, ())
            # This relies on the `yy_Latn` directory being actually present.
            assert paths.format_target_path("{locale}/c.pot", "yy-Latn") == join(
                paths.base, "yy_Latn", "c.pot"
            )
            assert paths.find_reference(join(root, "target", "zz", "a.ftl")) == (
                join(paths.ref_root, "a.ftl"),
                {"locale": "zz"},
            )
            assert paths.find_reference(join(root, "target", "yy_Latn", "c.po")) == (
                join(paths.ref_root, "c.pot"),
                {"locale": "yy-Latn"},
            )
            assert paths.find_reference(join(root, "target", "ignore", "a.ftl")) is None
            assert paths.find_reference(join(root, "target", "zz", "d.ftl")) is None

    def test_ref_root(self):
        tree: Tree = {
            "source": {
                "en": {"c.pot": ""},
                "en-US": {"a.ftl": "", "b.ftl": ""},
            },
            "empty": {"aa": {}, "bb": {}, "cc": {}, "dd": {}},
            "target": {
                "ignore": {"a.ftl": "", "b.ftl": ""},
                "zz": {"a.ftl": "", "b.ftl": ""},
                "yy_Latn": {"a.ftl": "", "b.ftl": ""},
            },
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)

            paths = L10nDiscoverPaths(root, ref_root="source")
            assert paths.ref_root == join(root, "source", "en")
            assert paths.base == join(root, "target")

            paths = L10nDiscoverPaths(root, ref_root="source/en-US")
            assert paths.ref_root == join(root, "source", "en-US")
            assert paths.base == join(root, "target")

            paths = L10nDiscoverPaths(root, ref_root="target")
            assert paths.ref_root == join(root, "target")
            assert paths.base == join(root, "empty")

            paths = L10nDiscoverPaths(root, ref_root="target/ignore")
            assert paths.ref_root == join(root, "target", "ignore")
            assert paths.base == join(root, "target")

            with self.assertRaises(MissingSourceDirectoryError):
                L10nDiscoverPaths(root, ref_root="empty")

            with self.assertRaises(MissingSourceDirectoryError):
                L10nDiscoverPaths(root, ref_root="missing")

    def test_ref_target_mixed(self):
        tree: Tree = {
            "en": {"c.pot": ""},
            "en-US": {"a.ftl": "", "b.ftl": ""},
            "ignore": {"a.ftl": "", "b.ftl": ""},
            "zz": {"a.ftl": "", "b.ftl": ""},
            "yy_Latn": {"a.ftl": "", "b.ftl": ""},
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)

            paths = L10nDiscoverPaths(root)
            assert paths.ref_root == join(root, "en")
            assert paths.base == root
            assert set(paths.locales) == set(["yy-Latn", "zz"])

            paths = L10nDiscoverPaths(root, ref_root=join(root, "en-US"))
            assert paths.ref_root == join(root, "en-US")
            assert paths.base == root
            assert set(paths.locales) == set(["yy-Latn", "zz"])
