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

import sys
from os import mkdir
from os.path import join, normpath
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Any, Dict, Union
from unittest import TestCase

from moz.l10n.paths import L10nConfigPaths, get_android_locale

if sys.version_info >= (3, 11):
    from tomllib import load
else:
    from tomli import load

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


class TestL10nConfigPaths(TestCase):
    def test_paths(self):
        cfg_toml = dedent(
            """
            [[paths]]
                reference = "en/one.pot"
                l10n = "{locale}/one.po"
            [[paths]]
                reference = "en/two/**"
                l10n = "{locale}/x/two/**"
            [[paths]]
                reference = "en/three/**/*.ftl"
                l10n = "{locale}/y/**/*.ftl"
            """
        )
        tree: Tree = {
            "cfg": cfg_toml,
            "en": {
                "one.pot": "",
                "two": {"a": "", "b.pot": ""},
                "three": {"c.ftl": "", "d": {"e.ftl": ""}, "f.ftl": {"g": ""}},
            },
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)
            paths = L10nConfigPaths(
                join(root, "cfg"), force_paths=[join(root, "en", "three", "extra.ftl")]
            )

        assert paths.base == root
        assert paths.locales is None
        expected = {
            (
                join(root, "en", normpath(ref)),
                join(root, "{locale}", normpath(tgt)),
            ): None
            for ref, tgt in {
                "one.pot": "one.po",
                "three/c.ftl": "y/c.ftl",
                "three/d/e.ftl": "y/d/e.ftl",
                "three/extra.ftl": "y/extra.ftl",
                "two/a": "x/two/a",
                "two/b.pot": "x/two/b.po",
            }.items()
        }
        assert paths.all() == expected
        for ref, tgt in expected:
            assert paths.target(ref) == (tgt, ())
        assert paths.find_reference("xx/one.po") == (
            join(root, "en", "one.pot"),
            {"locale": "xx"},
        )
        assert paths.find_reference("yy-YY/x/two/b.po") == (
            join(root, "en", "two", "b.pot"),
            {"locale": "yy-YY"},
        )
        assert paths.find_reference("xx-Latn-XX/y/d/e.ftl") == (
            join(root, "en", "three", "d", "e.ftl"),
            {"locale": "xx-Latn-XX"},
        )
        assert paths.find_reference("xx-Latn/y/extra.ftl") == (
            join(root, "en", "three", "extra.ftl"),
            {"locale": "xx-Latn"},
        )
        assert paths.find_reference("xx//") is None
        assert paths.find_reference("xx/x/two") is None
        assert paths.find_reference("xx/y/x/w.ftl") is None

    def test_firefox(self):
        browser_toml = dedent(
            """
            basepath = "../.."
            [env]
                l = "{l10n_base}/{locale}/"
            [[paths]]
                reference = "browser/locales/en-US/**"
                l10n = "{l}browser/**"
            [[paths]]
                reference = "browser/branding/locales/en-US/**"
                l10n = "{l}browser/branding/**"
            [[includes]]
                path = "devtools/shared/locales/l10n.toml"
            [[includes]]
                path = "toolkit/locales/l10n.toml"
            """
        )
        devtools_toml = dedent(
            """
            # included in both browser_toml and toolkit_toml
            basepath = "../../.."
            [[paths]]
                reference = "devtools/shared/locales/en-US/**"
                l10n = "{l10n_base}/{locale}/devtools/**"
            [[includes]]
                # reference loop
                path = "toolkit/locales/l10n.toml"
            """
        )
        toolkit_toml = dedent(
            """
            basepath = "../.."
            [env]
                l = "{l10n_base}/{locale}/"
            [[paths]]
                reference = "toolkit/locales/en-US/**"
                l10n = "{l}toolkit/**"
            [[paths]]
                reference = "dom/locales/en-US/**"
                l10n = "{l}dom/**"
            [[paths]]
                # duplicates path included in browser_toml
                reference = "browser/locales/en-US/b/**"
                l10n = "{l}browser/b/**"
            [[includes]]
                path = "devtools/shared/locales/l10n.toml"
            """
        )
        tree: Tree = {
            "browser": {
                "branding": {"locales": {"en-US": {"a": "", "b": {"c": ""}}}},
                "locales": {
                    "l10n.toml": browser_toml,
                    "en-US": {"a": "", "b": {"c": ""}},
                },
            },
            "devtools": {
                "shared": {
                    "locales": {
                        "l10n.toml": devtools_toml,
                        "en-US": {"a": "", "b": {"c": ""}},
                    }
                }
            },
            "dom": {
                "locales": {
                    "l10n.toml": "",
                    "en-US": {"a": "", "b": {"c": ""}},
                }
            },
            "toolkit": {
                "locales": {
                    "l10n.toml": toolkit_toml,
                    "en-US": {"a": "", "b": {"c": ""}},
                }
            },
        }
        loaded = []

        def cfg_load(cfg_path: str) -> dict[str, Any]:
            loaded.append(cfg_path)
            with open(cfg_path, mode="rb") as file:
                return load(file)

        with TemporaryDirectory() as root:
            build_file_tree(root, tree)
            paths = L10nConfigPaths(
                join(root, "browser", "locales", "l10n.toml"), cfg_load=cfg_load
            )

        assert loaded == [
            join(root, p, "locales", "l10n.toml")
            for p in ("browser", join("devtools", "shared"), "toolkit")
        ]
        assert paths.base == root
        assert paths.locales is None
        expected = {
            (join(root, normpath(ref)), join(root, "{locale}", normpath(tgt))): None
            for ref, tgt in {
                "browser/branding/locales/en-US/a": "browser/branding/a",
                "browser/branding/locales/en-US/b/c": "browser/branding/b/c",
                "browser/locales/en-US/a": "browser/a",
                "browser/locales/en-US/b/c": "browser/b/c",
                "devtools/shared/locales/en-US/a": "devtools/a",
                "devtools/shared/locales/en-US/b/c": "devtools/b/c",
                "dom/locales/en-US/a": "dom/a",
                "dom/locales/en-US/b/c": "dom/b/c",
                "toolkit/locales/en-US/a": "toolkit/a",
                "toolkit/locales/en-US/b/c": "toolkit/b/c",
            }.items()
        }
        assert paths.all() == expected
        for ref, tgt in expected:
            assert paths.target(ref) == (tgt, ())
        assert paths.target(join(root, "browser", "locales", "l10n.toml")) == (None, ())
        paths.locales = ["aa", "bb"]
        new_base = join(paths.base, "x", "y", "z")
        paths.base = new_base
        assert paths.all() == {
            (ref, tgt.replace(root, new_base)): ["aa", "bb"] for ref, tgt in expected
        }
        assert paths.find_reference("xx/dom/a") == (
            join(root, normpath("dom/locales/en-US/a")),
            {"locale": "xx"},
        )

    def test_fomo_buyersguide(self):
        cfg_toml = dedent(
            """
            basepath = "foundation/translations/networkapi"
            locales = ["de", "es", "fr", "fy-NL", "nl", "pl", "pt-BR", "sw"]
            [[paths]]
                reference = "wagtailpages/templates/buyersguide/locale/django.pot"
                l10n = "wagtailpages/templates/buyersguide/locale/{locale}/LC_MESSAGES/django.po"
            [[paths]]
                reference = "wagtailpages/templates/about/locale/django.pot"
                l10n = "wagtailpages/templates/about/locale/{locale}/LC_MESSAGES/django.po"
                locales = ["de", "es", "fr", "pt-BR"]
            [[paths]]
                reference = "templates/pages/buyersguide/about/locale/django.pot"
                l10n = "templates/pages/buyersguide/about/locale/{locale}/LC_MESSAGES/django.po"
                locales = ["de", "es", "fr", "pt-BR"]
            """
        )
        with TemporaryDirectory() as root:
            build_file_tree(root, {"l10n.toml": cfg_toml})
            paths = L10nConfigPaths(join(root, "l10n.toml"))
        assert paths.base == join(root, "foundation", "translations", "networkapi")
        assert paths.locales
        assert paths.locales == ["de", "es", "fr", "fy-NL", "nl", "pl", "pt-BR", "sw"]
        assert paths.all_locales == set(paths.locales)
        path_locales = ["de", "es", "fr", "pt-BR"]
        assert paths.all() == {
            (
                join(paths.base, normpath(path), "django.pot"),
                join(
                    paths.base, normpath(path), "{locale}", "LC_MESSAGES", "django.po"
                ),
            ): locales
            for path, locales in (
                ("wagtailpages/templates/buyersguide/locale", paths.locales),
                ("wagtailpages/templates/about/locale", path_locales),
                ("templates/pages/buyersguide/about/locale", path_locales),
            )
        }
        res_source = "wagtailpages/templates/about/locale/django.pot"
        res_target = (
            "wagtailpages/templates/about/locale/{locale}/LC_MESSAGES/django.po"
        )
        tgt_path, tgt_locales = paths.target(res_source)
        assert tgt_path
        assert tgt_path == join(paths.base, normpath(res_target))
        assert tgt_locales == set(path_locales)
        assert paths.format_target_path(tgt_path, "de") == join(
            paths.base,
            normpath(res_target).format(locale="de"),
        )

        paths.locales = ["es", "fr", "nl"]
        assert paths.target(res_source)[1] == set(("es", "fr"))
        assert paths.all_locales == {"es", "fr", "nl", "de", "pt-BR"}
        paths.locales = []
        assert paths.target(res_source)[1] == path_locales

    def test_fenix(self):
        cfg_toml = dedent(
            """
            locales = ["abc", "de-FG"]
            [[paths]]
                reference = "res/values/strings.xml"
                l10n = "res/values-{android_locale}/strings.xml"
            """
        )
        tree: Tree = {
            "l10n.toml": cfg_toml,
            "res": {
                "values": {"strings.xml": ""},
                "values-b+abc": {"strings.xml": ""},
                "values-b+de+FG": {"strings.xml": ""},
            },
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)
            paths = L10nConfigPaths(
                join(root, "l10n.toml"),
                locale_map={"android_locale": lambda lc: f"b+{lc.replace('-', '+')}"},
            )

        assert paths.base == paths.ref_root == root
        source_strings = join(root, "res", "values", "strings.xml")
        target_strings = join(root, "res", "values-{android_locale}", "strings.xml")
        assert paths.all() == {(source_strings, target_strings): ["abc", "de-FG"]}
        assert paths.target(source_strings) == (target_strings, ["abc", "de-FG"])
        assert paths.format_target_path(target_strings, "abc") == target_strings.format(
            android_locale="b+abc"
        )
        assert paths.format_target_path("foo/{android_locale}-xx/bar", "abc") == join(
            "foo", "b+abc-xx", "bar"
        )
        assert paths.find_reference("res/values-xx/strings.xml") == (
            source_strings,
            {"android_locale": "xx"},
        )
        assert paths.find_reference("res/values-b+de+FG/strings.xml") == (
            source_strings,
            {"android_locale": "b+de+FG"},
        )
        assert paths.find_reference("res/values-xx/nonesuch") is None

    def test_firefox_for_android(self):
        root_toml = dedent(
            """
            basepath = "."
            [[includes]]
                path = "mozilla-mobile/android-components/l10n.toml"
            """
        )
        ac_toml = dedent(
            """
            basepath = "."
            [[paths]]
                reference = "components/**/src/main/res/values/strings.xml"
                l10n = "components/**/src/main/res/values-{android_locale}/strings.xml"
            """
        )
        tree: Tree = {
            "l10n.toml": root_toml,
            "mozilla-mobile": {
                "android-components": {
                    "l10n.toml": ac_toml,
                    "components": {
                        "foo": {
                            "src": {
                                "main": {
                                    "res": {
                                        "values": {"strings.xml": ""},
                                        "values-fr": {"strings.xml": ""},
                                    }
                                }
                            }
                        }
                    },
                },
            },
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)
            paths = L10nConfigPaths(
                join(root, "l10n.toml"),
                locale_map={"android_locale": get_android_locale},
            )

        assert paths.base == root
        assert paths.locales is None
        res_path = normpath(
            "mozilla-mobile/android-components/components/foo/src/main/res"
        )
        rel_ref_path = join(res_path, normpath("values/strings.xml"))
        abs_ref_path = join(root, rel_ref_path)
        exp_tgt = join(root, res_path, normpath("values-{android_locale}/strings.xml"))
        assert paths.all() == {(abs_ref_path, exp_tgt): None}
        assert paths.target(abs_ref_path) == (exp_tgt, ())
        assert paths.target(rel_ref_path) == (exp_tgt, ())
        assert paths.find_reference("values-xx/strings.xml") is None
        assert paths.find_reference(join(res_path, "values-xx/strings.xml")) == (
            abs_ref_path,
            {"android_locale": "xx"},
        )
        assert paths.find_reference(join(res_path, "values-de-FG/strings.xml")) == (
            abs_ref_path,
            {"android_locale": "de-FG"},
        )
        assert paths.find_reference(exp_tgt.format(android_locale="b+de+FG")) == (
            abs_ref_path,
            {"android_locale": "b+de+FG"},
        )

    def test_thunderbird(self):
        mail_toml = dedent(
            """
            basepath = "../.."
            [env]
                l = "{l10n_base}/{locale}/"
                mozilla = ".."
            [[includes]]
                path = "{mozilla}/toolkit/locales/l10n.toml"
            [[includes]]
                path = "calendar/locales/l10n.toml"
            [[paths]]
                reference = "mail/locales/en-US/**"
                l10n = "{l}mail/**"
            """
        )
        calendar_toml = dedent(
            """
            basepath = "../.."
            [env]
                l = "{l10n_base}/{locale}/"
            [[paths]]
                reference = "calendar/locales/en-US/**"
                l10n = "{l}calendar/**"
            """
        )
        toolkit_toml = dedent(
            """
            basepath = "../.."
            [env]
                l = "{l10n_base}/{locale}/"
            [[paths]]
                reference = "toolkit/locales/en-US/**"
                l10n = "{l}toolkit/**"
            """
        )
        tree: Tree = {
            "comm": {
                "calendar": {
                    "locales": {
                        "l10n.toml": calendar_toml,
                        "en-US": {"calendar": {"calendar.ftl": ""}},
                    }
                },
                "mail": {
                    "locales": {
                        "l10n.toml": mail_toml,
                        "en-US": {"installer": {"override.properties": ""}},
                    }
                },
            },
            "toolkit": {
                "locales": {
                    "l10n.toml": toolkit_toml,
                    "en-US": {"toolkit": {"about": {"config.ftl": ""}}},
                }
            },
        }
        with TemporaryDirectory() as root:
            build_file_tree(root, tree)
            paths = L10nConfigPaths(join(root, "comm", "mail", "locales", "l10n.toml"))

        override = join("installer", "override.properties")
        config = join("toolkit", "about", "config.ftl")
        calendar = join("calendar", "calendar.ftl")
        assert set(paths.all()) == {
            (
                join(root, "comm", "mail", "locales", "en-US", override),
                join(root, "comm", "{locale}", "mail", override),
            ),
            (
                join(root, "toolkit", "locales", "en-US", config),
                join(root, "{locale}", "toolkit", config),
            ),
            (
                join(root, "comm", "calendar", "locales", "en-US", calendar),
                join(root, "comm", "{locale}", "calendar", calendar),
            ),
        }
        paths.base = join(root, "foo")
        assert set(tgt for _, tgt in paths.all()) == {
            join(root, "foo", "{locale}", "mail", override),
            join(root, "foo", "{locale}", "toolkit", config),
            join(root, "foo", "{locale}", "calendar", calendar),
        }

    def test_path_per_locale(self):
        cfg_toml = dedent(
            """
            basepath = "."
            locales = ["en", "es", "de"]

            [[paths]]
            reference = "translations/wordpress.pot"
            l10n = "translations/wordpress/wordpress-es_ES.po"
            locales = ["es"]

            [[paths]]
            reference = "translations/wordpress.pot"
            l10n = "translations/wordpress/wordpress-de_DE.po"
            locales = ["de"]

            [[paths]]
            reference = "translations/wordpress-react.pot"
            l10n = "translations/wordpress-react/wordpress-react-{locale}.po"
            """
        )
        with TemporaryDirectory() as root:
            build_file_tree(root, {"l10n.toml": cfg_toml})
            paths = L10nConfigPaths(join(root, "l10n.toml"))

        assert paths.all_locales == {"en", "es", "de"}
        assert paths.all() == {
            (
                join(root, normpath("translations/wordpress.pot")),
                join(root, normpath("translations/wordpress/wordpress-es_ES.po")),
            ): ["es"],
            (
                join(root, normpath("translations/wordpress.pot")),
                join(root, normpath("translations/wordpress/wordpress-de_DE.po")),
            ): ["de"],
            (
                join(root, normpath("translations/wordpress-react.pot")),
                join(
                    root,
                    normpath(
                        "translations/wordpress-react/wordpress-react-{locale}.po"
                    ),
                ),
            ): ["en", "es", "de"],
        }

        assert list(paths.ref_paths) == [
            join(root, normpath("translations/wordpress.pot")),
            join(root, normpath("translations/wordpress.pot")),
            join(root, normpath("translations/wordpress-react.pot")),
        ]

        none_path, none_locales = paths.target("translations/wordpress.pot")
        assert none_path == join(
            paths.base, normpath("translations/wordpress/wordpress-es_ES.po")
        )
        assert none_locales == {"es"}
        es_path, es_locales = paths.target("translations/wordpress.pot", locale="es")
        assert es_path == join(
            paths.base, normpath("translations/wordpress/wordpress-es_ES.po")
        )
        assert es_locales == {"es"}
        de_path, de_locales = paths.target("translations/wordpress.pot", locale="de")
        assert de_path == join(
            paths.base, normpath("translations/wordpress/wordpress-de_DE.po")
        )
        assert de_locales == {"de"}

        paths.locales = ["en", "de"]
        lim_path, lim_locales = paths.target("translations/wordpress.pot")
        assert lim_path == join(
            paths.base, normpath("translations/wordpress/wordpress-es_ES.po")
        )
        assert lim_locales == ()

        set_path, set_locales = paths.target(
            "translations/wordpress-react.pot", locale="de"
        )
        assert set_path == join(
            paths.base, normpath("translations/wordpress-react/wordpress-react-de.po")
        )
        assert set_locales == {"de"}
