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
from unittest import SkipTest, TestCase

from moz.l10n.migrate import apply_migration, copy
from moz.l10n.migrate.utils import get_pattern, plural_message

from .test_config import Tree, build_file_tree

try:
    import moz.l10n.formats.android  # noqa: F401
except ImportError:
    raise SkipTest("Requires [xml] extra")


class TestMigrate(TestCase):
    def test_android(self):
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
              <string name="x-one">%1$d thing</string>
              <string name="x-other">%1$d things</string>
              <string name="y">Y</string>
              <string name="w">W</string>
            </resources>
            """
        )
        foo_de = dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <resources>
              <string name="y">Y</string>
              <string name="y2">Y2</string>
              <string name="z2">Z2</string>
              <string name="w">W</string>
            </resources>
            """
        )
        bar = dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <resources>
              <string name="z">bar Z</string>
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
            "bar": {
                "values": {"strings.xml": ""},
                "values-fr": {"strings.xml": bar},
                "values-de": {"strings.xml": bar},
            },
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)

            def make_plural_x(res, _):
                x_other = get_pattern(res, "x-other")
                x_one = get_pattern(res, "x-one", default=x_other)
                x_two = get_pattern(res, "x-two", default=x_other)
                msg = plural_message("quantity", one=x_one, two=x_two, other=x_other)
                return msg, {"x-one", "x-two", "x-other"}

            apply_migration(
                join(root, "l10n.toml"),
                {
                    "foo/values/strings.xml": {
                        "x": make_plural_x,
                        "y2": copy(None, "y"),
                        "z2": copy("bar/values/strings.xml", "z"),
                    }
                },
            )

            with open(join(root, "foo", "values-fr", "strings.xml"), mode="r") as file:
                assert file.read() == dedent(
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
                      <string name="y">Y</string>
                      <string name="y2">Y</string>
                      <string name="w">W</string>
                      <string name="z2">bar Z</string>
                    </resources>
                    """
                )

            with open(join(root, "foo", "values-de", "strings.xml"), mode="r") as file:
                assert file.read() == foo_de

    def test_discover(self):
        a_ftl = dedent(
            """\
            a1 = A1
            a2 = { $n ->
                [one] A2-1
               *[other] A2-*
              }
            """
        )
        c_ini = "[Strings]\nc1=C\n"
        tree: Tree = {
            "en-US": {"a.ftl": a_ftl, "b.ftl": "", "c.ini": "", "d.ini": "[Strings]\n"},
            "fr": {"a.ftl": a_ftl, "b.ftl": "", "c.ini": c_ini, "d.ini": "[Strings]\n"},
            "de_Test": {"a.ftl": a_ftl, "c.ini": c_ini},
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)

            apply_migration(
                root,
                {
                    "b.ftl": {
                        "b1": copy("a.ftl", "a1"),
                        "b2": copy("a.ftl", "a2", variant="one"),
                    },
                    "d.ini": {
                        ("Strings", "d1"): copy("c.ini", ("Strings", "c1")),
                    },
                },
            )

            for locale in ["fr", "de_Test"]:
                with open(join(root, locale, "b.ftl")) as file:
                    assert file.read() == "b1 = A1\n" + "b2 = A2-1\n"

                with open(join(root, locale, "d.ini")) as file:
                    assert file.read() == "[Strings]\n" + "d1=C\n"
