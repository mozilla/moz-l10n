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

from os.path import isfile, join
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import SkipTest, TestCase

from moz.l10n.bin.migrate import cli
from moz.l10n.migrate import Migrate, copy
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

            Migrate(
                {
                    "foo/values/strings.xml": {
                        "x": make_plural_x,
                        "y2": copy(None, "y"),
                        "z2": copy("bar/values/strings.xml", "z"),
                    }
                },
                join(root, "l10n.toml"),
            ).apply()

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
                      <string name="w">W</string>
                      <string name="z2">bar Z</string>
                    </resources>
                    """
                )

            with open(join(root, "foo", "values-de", "strings.xml")) as file:
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

    def test_cli(self):
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

            with self.assertRaises(SystemExit) as exit:
                cli([join(root, "migration.py")])
            assert exit.exception.code == 2

            with self.assertRaises(SystemExit) as exit:
                cli(
                    [
                        "--config",
                        join(root, "l10n.toml"),
                        "--root",
                        root,
                        join(root, "migration.py"),
                    ]
                )
            assert exit.exception.code == 2

            with self.assertRaises(SystemExit) as exit:
                cli(["--root", root, join(root, "does-not-exist.py")])
            assert exit.exception.code == 2

            with self.assertRaises(SystemExit) as exit:
                cli(["--root", root, join(root, "bad_migration.py")])
            assert exit.exception.code == 2

            cli(["--root", root, "--dry-run", join(root, "migration.py")])
            with open(join(root, "fr", "b.ftl")) as file:
                assert file.read() == ""
            with open(join(root, "fr", "d.ini")) as file:
                assert file.read() == "[Strings]\n"
            assert not isfile(join(root, "de_Test", "b.ftl"))
            assert not isfile(join(root, "de_Test", "d.ini"))

            cli(["--root", root, join(root, "migration.py")])
            for locale in ["fr", "de_Test"]:
                with open(join(root, locale, "b.ftl")) as file:
                    assert file.read() == "b1 = A1\n" + "b2 = A2-1\n"

                with open(join(root, locale, "d.ini")) as file:
                    assert file.read() == "[Strings]\n" + "d1=C\n"

    def test_firefox_plural_properties(self):
        migration = dedent(
            """\
            import re
            from typing import cast

            from moz.l10n.migrate import Migrate
            from moz.l10n.migrate.utils import MigrationContext, get_entry
            from moz.l10n.model import (
                CatchallKey,
                Expression,
                PatternMessage,
                SelectMessage,
                VariableRef,
            )


            def parse_pattern(src: str):
                pos = 0
                for m in re.finditer(r"#1|#2|%d", src):
                    start = m.start()
                    if start > pos:
                        yield src[pos:start]
                    yield Expression(VariableRef("n" if m[0] == "#1" else "x"))
                    pos = m.end()
                if pos < len(src):
                    yield src[pos:]


            def get_key(locale: str, idx: int):
                if locale in {"ltg", "lv"}:
                    categories = ["zero", "one", CatchallKey("other")]
                elif locale in {"bs", "hr", "lt", "ro", "sr"}:
                    categories = ["one", "few", CatchallKey("other")]
                elif locale in {"be", "cs", "pl", "ru", "sk", "szl", "uk"}:
                    categories = ["one", "few", CatchallKey("many")]
                elif locale in {"dsb", "gd", "hsb", "sl"}:
                    categories = ["one", "two", "few", CatchallKey("other")]
                elif locale in {"br", "ga"}:
                    categories = ["one", "two", "few", "many", CatchallKey("other")]
                elif locale == "ar":
                    categories = ["one", "two", "few", "many", CatchallKey("other"), "zero"]
                elif locale == "cy":
                    categories = ["zero", "one", "two", "few", "many", CatchallKey("other")]
                else:
                    categories = ["one", CatchallKey("other")]
                return categories[idx if idx < len(categories) else -1]


            plural_categories = ["zero", "one", "two", "few", "many", "other"]


            def plural(ref_path: str, id: str):
                def plural_(_, ctx: MigrationContext):
                    res = ctx.get_resource(ref_path)
                    if res is None:
                        return None
                    entry = get_entry(res, id)
                    if entry is None:
                        return None
                    pattern = cast(PatternMessage, entry.value).pattern
                    assert len(pattern) == 1
                    assert isinstance(pattern[0], str)
                    parts = pattern[0].split(";")

                    if len(parts) > 1:
                        var_list = [
                            (get_key(ctx.locale, idx), part) for idx, part in enumerate(parts)
                        ]
                        var_list.sort(
                            key=lambda v: plural_categories.index(k)
                            if isinstance(k := v[0], str) and k in plural_categories
                            else 6
                        )
                        entry.value = SelectMessage(
                            {"n": Expression(VariableRef("n"), "number")},
                            (VariableRef("n"),),
                            {(key,): list(parse_pattern(part)) for key, part in var_list},
                        )

                    entry.comment = re.sub(
                        r"LOCALIZATION NOTE.*?:|Semi-colon list of plural forms.|See: http.*?/Localization_and_Plurals",
                        "",
                        entry.comment,
                    ).strip()

                    return (entry, {id})

                return plural_


            Migrate(
                {
                    "debugger.ftl": {
                        "source-search-results-summary": plural(
                            "debugger.properties", "sourceSearch.resultsSummary2"
                        ),
                        "editor-search-results": plural(
                            "debugger.properties", "editor.searchResults1"
                        ),
                    }
                }
            )
            """
        )

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
            "migration.py": migration,
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)

            cli(["--root", root, join(root, "migration.py")])
            with open(join(root, "fr", "debugger.ftl"), encoding="utf-8") as file:
                assert file.read() == dedent("""\
                    # Shows a summary of the number of matches for autocomplete
                    source-search-results-summary =
                        { $n ->
                            [one] { NUMBER($n) } résultat
                           *[other] { NUMBER($n) } résultats
                        }
                    # Editor Search bar message to summarize the selected search result. e.g. 5 of 10 results.
                    editor-search-results =
                        { $n ->
                            [one] Résultat { $x } sur { NUMBER($n) }
                           *[other] Résultat { $x } sur { NUMBER($n) }
                        }
                """)
            with open(join(root, "lt", "debugger.ftl"), encoding="utf-8") as file:
                assert file.read() == dedent("""\
                    source-search-results-summary =
                        { $n ->
                            [one] { NUMBER($n) } rezultatas
                            [few] { NUMBER($n) } rezultatai
                           *[other] { NUMBER($n) } rezultatų
                        }
                    editor-search-results =
                        { $n ->
                            [one] { $x } iš { NUMBER($n) } rezultato
                            [few] { $x } iš { NUMBER($n) } rezultatų
                           *[other] { $x } iš { NUMBER($n) } rezultatų
                        }
                """)
            with open(join(root, "uk", "debugger.ftl"), encoding="utf-8") as file:
                assert file.read() == dedent("""\
                    source-search-results-summary =
                        { $n ->
                            [one] { NUMBER($n) } результат
                            [few] { NUMBER($n) } результати
                           *[many] { NUMBER($n) } результатів
                        }
                    editor-search-results =
                        { $n ->
                            [one] { $x } результат з { NUMBER($n) }
                            [few] { $x } результати з { NUMBER($n) }
                           *[many] { $x } результатів з { NUMBER($n) }
                        }
                """)
            with open(join(root, "ar", "debugger.ftl"), encoding="utf-8") as file:
                assert file.read() == dedent("""\
                    source-search-results-summary =
                        { $n ->
                            [zero] لا نتائج
                            [one] نتيجة واحدة
                            [two] نتيجتان
                            [few] { NUMBER($n) } نتائج
                            [many] { NUMBER($n) } نتيجة
                           *[other] { NUMBER($n) } نتيجة
                        }
                    editor-search-results =
                        { $n ->
                            [zero] لا نتائج
                            [one] نتيجة واحدة
                            [two] { $x } من أصل نتيجتين
                            [few] { $x } من أصل { NUMBER($n) } نتائج
                            [many] { $x } من أصل { NUMBER($n) } نتيجة
                           *[other] { $x } من أصل { NUMBER($n) } نتيجة
                        }
                """)
