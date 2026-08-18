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

from importlib.resources import files
from os.path import isfile, join
from tempfile import TemporaryDirectory
from textwrap import dedent

import moz.l10n.bin
import pytest
from click.testing import CliRunner

from ..utils import Tree, build_file_tree

pytest.importorskip("moz.l10n.formats.android", reason="Requires [xml] extra")


def test_android() -> None:
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
    migration = dedent(
        """\
        from moz.l10n.migrate import Migrate, copy
        from moz.l10n.migrate.utils import get_pattern, plural_message

        def make_plural_x(res, _):
            x_other = get_pattern(res, "x-other")
            x_one = get_pattern(res, "x-one", default=x_other)
            x_two = get_pattern(res, "x-two", default=x_other)
            msg = plural_message("quantity", one=x_one, two=x_two, other=x_other)
            return msg, {"x-one", "x-two", "x-other"}

        Migrate(
            {
                "foo/values/strings.xml": {
                    "x": make_plural_x,
                    "y2": copy(None, "y"),
                    "z2": copy("bar/values/strings.xml", "z"),
                }
            }
        )

        """
    )
    tree: Tree = {
        "l10n.toml": cfg_toml,
        "migration.py": migration,
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

        runner = CliRunner()
        # fmt: off
        result = runner.invoke(moz.l10n.bin.cli, ["migrate",
            "--config", join(root, "l10n.toml"),
            join(root, "migration.py"),
        ])
        assert result.exit_code == 0
        # fmt: on
        with open(join(root, "foo", "values-fr", "strings.xml")) as file:
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
                  <string name="z2">bar Z</string>
                  <string name="w">W</string>
                </resources>
                """
            )

        with open(join(root, "foo", "values-de", "strings.xml")) as file:
            assert file.read() == foo_de


def test_cli() -> None:
    bad_migration = "Migrate({})"
    migration = dedent(
        """\
        from moz.l10n.migrate import Migrate, copy

        Migrate({
            "b.ftl": {
                "b1": copy("a.ftl", "a1"),
                "b2": copy("a.ftl", "a2", variant="one"),
            },
        })

        Migrate({
            "d.ini": {
                ("Strings", "d1"): copy("c.ini", ("Strings", "c1")),
            },
        })
        """
    )
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
        "bad_migration.py": bad_migration,
        "migration.py": migration,
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(
            moz.l10n.bin.cli, ["migrate", join(root, "migration.py")]
        )
        assert result.exit_code == 2

        # fmt: off
        result = runner.invoke( moz.l10n.bin.cli, ["migrate",
                "--config", join(root, "l10n.toml"),
                "--root", root,
                join(root, "migration.py"),
        ])
        assert result.exit_code == 2

        result = runner.invoke(moz.l10n.bin.cli, ["migrate",
            "--root", root,
            join(root, "does-not-exist.py")
        ])
        assert result.exit_code == 2

        result = runner.invoke(moz.l10n.bin.cli, ["migrate",
            "--root", root, join(root, "bad_migration.py")
        ])
        assert result.exit_code == 2

        result = runner.invoke(moz.l10n.bin.cli, ["migrate",
            "--root", root,
            "--dry-run",
            join(root, "migration.py")
        ])
        assert result.exit_code == 0
        # fmt: on

        with open(join(root, "fr", "b.ftl")) as file:
            assert file.read() == ""
        with open(join(root, "fr", "d.ini")) as file:
            assert file.read() == "[Strings]\n"
        assert not isfile(join(root, "de_Test", "b.ftl"))
        assert not isfile(join(root, "de_Test", "d.ini"))

        result = runner.invoke(
            moz.l10n.bin.cli, ["migrate", "--root", root, join(root, "migration.py")]
        )
        assert result.exit_code == 0

        for locale in "fr", "de_Test":
            with open(join(root, locale, "b.ftl")) as file:
                assert file.read() == "b1 = A1\n" + "b2 = A2-1\n"

            with open(join(root, locale, "d.ini")) as file:
                assert file.read() == "[Strings]\n" + "d1=C\n"


def test_firefox_plural_properties() -> None:
    tree: Tree = {
        "en-US": {"debugger.ftl": "", "debugger.properties": ""},
        "fr": {
            "debugger.properties": dedent("""\
                # LOCALIZATION NOTE (sourceSearch.resultsSummary2): Semi-colon list of plural forms.
                # See: http://developer.mozilla.org/en/docs/Localization_and_Plurals
                # Shows a summary of the number of matches for autocomplete
                sourceSearch.resultsSummary2 = #1 résultat;#1 résultats

                # LOCALIZATION NOTE (editor.searchResults1): Semi-colon list of plural forms.
                # See: http://developer.mozilla.org/en/docs/Localization_and_Plurals
                # Editor Search bar message to summarize the selected search result. e.g. 5 of 10 results.
                editor.searchResults1 = Résultat %d sur #1;Résultat %d sur #1
            """)
        },
        "lt": {
            "debugger.properties": dedent("""\
                sourceSearch.resultsSummary2 = #1 rezultatas;#1 rezultatai;#1 rezultatų
                editor.searchResults1 = %d iš #1 rezultato;%d iš #1 rezultatų;%d iš #1 rezultatų
            """)
        },
        "uk": {
            "debugger.properties": dedent("""\
                sourceSearch.resultsSummary2 = #1 результат;#1 результати;#1 результатів
                editor.searchResults1 = %d результат з #1;%d результати з #1;%d результатів з #1
            """)
        },
        "ar": {
            "debugger.properties": dedent("""\
                sourceSearch.resultsSummary2 = نتيجة واحدة;نتيجتان;#1 نتائج;#1 نتيجة;#1 نتيجة;لا نتائج
                editor.searchResults1 = نتيجة واحدة;%d من أصل نتيجتين;%d من أصل #1 نتائج;%d من أصل #1 نتيجة;%d من أصل #1 نتيجة;لا نتائج
            """)
        },
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        migration_path = files("tests.fixtures").joinpath(
            "migrate_pluralform_properties_to_fluent.py"
        )

        runner = CliRunner()
        result = runner.invoke(
            moz.l10n.bin.cli, ["migrate", "--root", root, str(migration_path)]
        )
        result

        with open(join(root, "fr", "debugger.ftl"), encoding="utf-8") as file:
            assert file.read() == dedent("""\
                # Shows a summary of the number of matches for autocomplete
                source-search-results-summary =
                    { $n ->
                        [one] { $n } résultat
                       *[other] { $n } résultats
                    }
                # Editor Search bar message to summarize the selected search result. e.g. 5 of 10 results.
                editor-search-results =
                    { $n ->
                        [one] Résultat { $x } sur { $n }
                       *[other] Résultat { $x } sur { $n }
                    }
            """)
        with open(join(root, "lt", "debugger.ftl"), encoding="utf-8") as file:
            assert file.read() == dedent("""\
                source-search-results-summary =
                    { $n ->
                        [one] { $n } rezultatas
                        [few] { $n } rezultatai
                       *[other] { $n } rezultatų
                    }
                editor-search-results =
                    { $n ->
                        [one] { $x } iš { $n } rezultato
                        [few] { $x } iš { $n } rezultatų
                       *[other] { $x } iš { $n } rezultatų
                    }
            """)
        with open(join(root, "uk", "debugger.ftl"), encoding="utf-8") as file:
            assert file.read() == dedent("""\
                source-search-results-summary =
                    { $n ->
                        [one] { $n } результат
                        [few] { $n } результати
                       *[many] { $n } результатів
                    }
                editor-search-results =
                    { $n ->
                        [one] { $x } результат з { $n }
                        [few] { $x } результати з { $n }
                       *[many] { $x } результатів з { $n }
                    }
            """)
        with open(join(root, "ar", "debugger.ftl"), encoding="utf-8") as file:
            assert file.read() == dedent("""\
                source-search-results-summary =
                    { $n ->
                        [zero] لا نتائج
                        [one] نتيجة واحدة
                        [two] نتيجتان
                        [few] { $n } نتائج
                        [many] { $n } نتيجة
                       *[other] { $n } نتيجة
                    }
                editor-search-results =
                    { $n ->
                        [zero] لا نتائج
                        [one] نتيجة واحدة
                        [two] { $x } من أصل نتيجتين
                        [few] { $x } من أصل { $n } نتائج
                        [many] { $x } من أصل { $n } نتيجة
                       *[other] { $x } من أصل { $n } نتيجة
                    }
            """)


def test_multi_arg_value_error() -> None:
    """Test catching `ValueError` raised during apply with more than one arg."""
    a_ftl = "a1 = A1\n"
    migration = dedent(
        """\
        from moz.l10n.migrate import Migrate

        def boom(res, ctx):
            raise ValueError("first arg", "second arg")

        Migrate({"a.ftl": {"new-id": boom}})
        """
    )
    tree: Tree = {
        "en-US": {"a.ftl": a_ftl},
        "fr": {"a.ftl": a_ftl},
        "migration.py": migration,
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(
            moz.l10n.bin.cli,
            ["migrate", "--root", root, join(root, "migration.py")],
        )
        assert result.exit_code == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
