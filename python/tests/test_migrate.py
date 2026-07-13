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

import pytest
from moz.l10n.migrate import Migrate, copy, entry
from moz.l10n.model import Entry, Expression, PatternMessage, VariableRef
from moz.l10n.paths.discover import L10nDiscoverPaths, MissingSourceDirectoryError

from .utils import Tree, build_file_tree

pytest.importorskip("moz.l10n.formats.android", reason="Requires [xml] extra")


def test_discover() -> None:
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

        migrate = Migrate(
            {
                "b.ftl": {
                    "b1": copy("a.ftl", "a1"),
                    "b2": copy("a.ftl", "a2", variant="one"),
                },
                "d.ini": {
                    ("Strings", "d1"): copy("c.ini", ("Strings", "c1")),
                },
            }
        )
        migrate.set_paths(root)
        migrate.apply()

        for locale in ["fr", "de_Test"]:
            with open(join(root, locale, "b.ftl")) as file:
                assert file.read() == "b1 = A1\n" + "b2 = A2-1\n"

            with open(join(root, locale, "d.ini")) as file:
                assert file.read() == "[Strings]\n" + "d1=C\n"


def test_ref_root() -> None:
    a_ftl = "a1 = A1\n"
    tree: Tree = {
        "ref": {"a.ftl": a_ftl, "b.ftl": ""},
        "root": {
            "fr": {"a.ftl": a_ftl, "b.ftl": ""},
            "de_Test": {"a.ftl": a_ftl},
        },
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        migrate = Migrate({"b.ftl": {"b1": copy("a.ftl", "a1")}})
        with pytest.raises(MissingSourceDirectoryError):
            migrate.set_paths(join(root, "root"))

        paths = L10nDiscoverPaths(join(root, "root"), ref_root=join(root, "ref"))
        migrate.set_paths(paths)
        migrate.apply()

        with open(join(root, "ref", "b.ftl")) as file:
            assert file.read() == ""
        for locale in ["fr", "de_Test"]:
            with open(join(root, "root", locale, "b.ftl")) as file:
                assert file.read() == "b1 = A1\n"


def test_copy() -> None:
    b_ftl = dedent("""\
        prev = Value { $x }
            .prop = Prop { "a" }
    """)
    tree: Tree = {
        "en-US": {"a.properties": "", "b.ftl": ""},
        "fr": {
            "a.properties": "key = Refresh %S…\n",
            "b.ftl": b_ftl,
        },
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        res = Migrate(
            {
                "b.ftl": {
                    "from-value": copy("b.ftl", "prev", value_only=True),
                    "from-prop": copy("b.ftl", "prev", property="prop"),
                    "replaced-value": copy(
                        None,
                        "prev",
                        value_only=True,
                        replace=lambda ph: Expression(VariableRef("y"))
                        if isinstance(ph, Expression)
                        else None,
                    ),
                    "replaced-prop": copy(
                        None,
                        "prev",
                        property="prop",
                        replace=lambda ph: Expression("b")
                        if isinstance(ph, Expression)
                        else None,
                    ),
                    "replaced-remote": copy(
                        "a.properties",
                        "key",
                        replace=lambda ph: Expression("-term", function="message")
                        if isinstance(ph, Expression) and ph.arg == VariableRef("arg")
                        else None,
                    ),
                }
            },
            paths=root,
            properties_printf_placeholders=True,
        ).apply()

        assert list(res.values()) == [
            [
                Entry(
                    ("from-value",),
                    PatternMessage(["Value ", Expression(VariableRef("x"))]),
                ),
                Entry(("from-prop",), PatternMessage(["Prop ", Expression("a")])),
                Entry(
                    ("replaced-value",),
                    PatternMessage(["Value ", Expression(VariableRef("y"))]),
                ),
                Entry(("replaced-prop",), PatternMessage(["Prop ", Expression("b")])),
                Entry(
                    ("replaced-remote",),
                    PatternMessage(
                        ["Refresh ", Expression("-term", "message"), "\u2026"]
                    ),
                ),
            ]
        ]

        with open(join(root, "fr", "b.ftl"), encoding="utf-8") as file:
            assert file.read() == dedent("""\
                prev = Value { $x }
                    .prop = Prop { "a" }
                from-value = Value { $x }
                from-prop = Prop { "a" }
                replaced-value = Value { $y }
                replaced-prop = Prop { "b" }
                replaced-remote = Refresh { -term }…
            """)


def test_entry() -> None:
    tree: Tree = {
        "en-US": {"a.properties": "", "b.ftl": ""},
        "fr": {
            "a.properties": dedent("""\
                # LOCALIZATION NOTE: %S is brandShortName.
                button.label = Refresh %S…
                button.accesskey = e
            """),
            "b.ftl": dedent("""\
                prev = Value
                    .prop = Prop
            """),
        },
        "de": {
            "a.properties": dedent("""\
                # LOCALIZATION NOTE: %S is brandShortName.
                button.label = Refresh %S…
            """),
            "b.ftl": dedent("""\
                prev = Value
                    .prop = Prop
            """),
        },
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        Migrate(
            {
                "b.ftl": {
                    "to-value": entry(value=copy("b.ftl", "prev")),
                    "to-prop": entry(properties={"prop": copy("b.ftl", "prev")}),
                    "button": entry(
                        copy("a.properties", "button.label"),
                        properties={
                            "accesskey": copy("a.properties", "button.accesskey"),
                        },
                    ),
                    "partial": entry(
                        copy("a.properties", "button.label"),
                        properties={
                            "accesskey": copy("a.properties", "button.accesskey"),
                        },
                        allow_partial=True,
                        comment="",
                    ),
                    "literal": entry(
                        "Fixed value",
                        properties={
                            "prop": PatternMessage(["Fixed ", Expression("pattern")])
                        },
                    ),
                }
            },
            paths=root,
            properties_printf_placeholders=True,
        ).apply()

        with open(join(root, "fr", "b.ftl"), encoding="utf-8") as file:
            assert file.read() == dedent("""\
                prev = Value
                    .prop = Prop
                to-value = Value
                to-prop =
                    .prop = Value
                # LOCALIZATION NOTE: %S is brandShortName.
                button = Refresh { $arg }…
                    .accesskey = e
                partial = Refresh { $arg }…
                    .accesskey = e
                literal = Fixed value
                    .prop = Fixed { "pattern" }
            """)
        with open(join(root, "de", "b.ftl"), encoding="utf-8") as file:
            assert file.read() == dedent("""\
                prev = Value
                    .prop = Prop
                to-value = Value
                to-prop =
                    .prop = Value
                partial = Refresh { $arg }…
                literal = Fixed value
                    .prop = Fixed { "pattern" }
            """)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
