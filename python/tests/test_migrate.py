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
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Any
from unittest import SkipTest, TestCase

from moz.l10n.migrate import (
    apply_migration,
    get_entry,
    get_pattern,
    plural_message,
)
from moz.l10n.paths import L10nConfigPaths, get_android_locale

from .test_config import Tree, build_file_tree

try:
    from moz.l10n.formats.android import android_parse, android_serialize
except ImportError:
    raise SkipTest("Requires [xml] extra")


class TestMigrate(TestCase):
    def test_android_plural(self):
        src = dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <resources>
              <string name="x-one">%1$d thing</string>
              <string name="x-other">%1$d things</string>
              <string name="y">next</string>
            </resources>
            """
        )

        res = android_parse(src)

        def make_plural_x(res, ctx):
            x_other = get_pattern(res, "x-other")
            x_one = get_pattern(res, "x-one", default=x_other)
            x_two = get_pattern(res, "x-two", default=x_other)
            msg = plural_message("quantity", one=x_one, two=x_two, other=x_other)
            return msg, ("x-one", "x-other")

        apply_migration(res, {"x": make_plural_x})

        ser = "".join(android_serialize(res))
        assert ser == dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <resources>
              <string name="x-one">%1$d thing</string>
              <string name="x-other">%1$d things</string>
              <plurals name="x">
                <item quantity="one">%1$d thing</item>
                <item quantity="two">%1$d things</item>
                <item quantity="other">%1$d things</item>
              </plurals>
              <string name="y">next</string>
            </resources>
            """
        )

    def test_android_paths(self):
        cfg_toml = dedent(
            """
            locales = ["fr", "de"]
            [[paths]]
                reference = "**/values/strings.xml"
                l10n = "**/values-{android_locale}/strings.xml"
            """
        )
        foo_fr = dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <resources>
              <string name="x">X</string>
              <string name="y">Y</string>
            </resources>
            """
        )
        foo_de = dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <resources>
              <string name="x">X</string>
              <string name="x2">X2</string>
              <string name="y">Y</string>
            </resources>
            """
        )
        tree: Tree = {
            "l10n.toml": cfg_toml,
            "foo": {
                "values": {"strings.xml": ""},
                "values-fr": {"strings.xml": foo_fr},
                "values-de": {"strings.xml": foo_de},
            },
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)
            paths = L10nConfigPaths(
                join(root, "l10n.toml"),
                locale_map={"android_locale": get_android_locale},
            )

            changes: Any = {
                "x2": lambda res, _: get_entry(res, "x"),
            }

            tgt_fmt, locales = paths.target(join("foo", "values", "strings.xml"))
            assert tgt_fmt
            for locale in locales:
                tgt_path = paths.format_target_path(tgt_fmt, locale)
                apply_migration(tgt_path, changes, {"locale": locale})

            with open(paths.format_target_path(tgt_fmt, "fr"), mode="r") as file:
                assert file.read() == dedent(
                    """\
                    <?xml version="1.0" encoding="utf-8"?>
                    <resources>
                      <string name="x">X</string>
                      <string name="x2">X</string>
                      <string name="y">Y</string>
                    </resources>
                    """
                )

            with open(paths.format_target_path(tgt_fmt, "de"), mode="r") as file:
                assert file.read() == foo_de
