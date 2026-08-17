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

from dataclasses import dataclass

import moz.l10n.lint
import pytest

FORMAT_MAP = {
    "android": "xml",
    "xcode": "xml",
    "fluent": "ftl",
    "gettext": "po",
    "webext": "json",
}


@dataclass
class MockResource:
    format: str
    path: str
    allows_empty_translations: bool = False


@dataclass
class MockEntity:
    string: str
    resource: MockResource


@pytest.fixture
def mock_entity():
    def _factory(
        resource_format: str,
        *,
        string: str = "",
        allows_empty_translations: bool = False,
    ) -> MockEntity:
        return MockEntity(
            string=string,
            resource=MockResource(
                format=resource_format,
                path=f"test.{FORMAT_MAP.get(resource_format, resource_format)}",
                allows_empty_translations=allows_empty_translations,
            ),
        )

    return _factory


def run_custom_checks(
    entity: MockEntity,
    string: str,
) -> dict[str, list[str]]:
    context = moz.l10n.lint.LintContext(
        resource_format=entity.resource.format,
        allows_empty_translations=entity.resource.allows_empty_translations,
        raw_source=entity.string,
        raw_translation=string,
    )

    diagnostics = moz.l10n.lint.check(context)

    # Map moz-l10n Diagnostic objects to Pontoon's expected dictionary
    errors = [d.message for d in diagnostics if d.severity == "error"]
    warnings = [d.message for d in diagnostics if d.severity == "warning"]

    checks: dict[str, list[str]] = {}
    if errors:
        checks["pErrors"] = errors
    if warnings:
        checks["pndbWarnings"] = warnings

    return checks


empty_error = ["Empty translations are not allowed"]
plural_error = ["Plural translation requires plural source"]


def test_ending_newline(mock_entity):
    """
    Original and translation in a PO file must either both end
    in a newline, or none of them should.
    """
    po_entity = mock_entity("gettext", string="Original")
    assert run_custom_checks(po_entity, "Translation\n") == {
        "pErrors": ["Ending newline mismatch"]
    }
    assert run_custom_checks(po_entity, "Translation") == {}

    po_entity.string = "Original\n"
    assert run_custom_checks(po_entity, "Translation") == {
        "pErrors": ["Ending newline mismatch"]
    }
    assert run_custom_checks(po_entity, "Translation\n") == {}


def test_empty_translations_allowed(mock_entity):
    """
    Empty translations should be allowed but noted for some extensions.
    """
    assert run_custom_checks(
        mock_entity("properties", allows_empty_translations=True), ""
    ) == {"pndbWarnings": ["Empty translation"]}


def test_empty_translations_not_allowed(mock_entity):
    """
    Empty translations shouldn't be allowed for some extensions.
    """
    po_entity = mock_entity("gettext")
    assert run_custom_checks(po_entity, "") == {"pErrors": empty_error}
    assert run_custom_checks(po_entity, "{{}}") == {"pErrors": empty_error}
    assert run_custom_checks(po_entity, ".input {$n :number} .match $n * {{}}") == {
        "pErrors": empty_error + plural_error
    }
    assert run_custom_checks(
        po_entity, ".input {$n :number} .match $n 1 {{}} * {{other}}"
    ) == {"pErrors": empty_error + plural_error}
    assert run_custom_checks(po_entity, "{{{||}}}") == {}

    assert run_custom_checks(
        mock_entity("fluent", string="key = value"), 'key = { "" }'
    ) == {"pndbWarnings": ["Empty translation"]}

    assert (
        run_custom_checks(mock_entity("fluent", string="key = value"), 'key = { "x" }')
        == {}
    )

    assert run_custom_checks(
        mock_entity("fluent", string="key =\n  .attr = value"),
        """key =
              { $var ->
                  [a] { "" }
                 *[b] { "" }
              }
              .attr = { "" }
            """,
    ) == {"pndbWarnings": ["Empty translation"]}

    assert run_custom_checks(
        mock_entity("fluent", string="key =\n  .attr = value"),
        """key =
              { $var ->
                  [a] { "x" }
                 *[b] { "y" }
              }
              .attr = { "" }
            """,
    ) == {"pndbWarnings": ["Empty translation"]}

    assert run_custom_checks(
        mock_entity("fluent", string="key =\n  .attr = value"),
        """key =
              { $var ->
                  [a] { "x" }
                 *[b] { "" }
              }
              .attr = { "y" }
            """,
    ) == {"pndbWarnings": ["Empty translation"]}

    assert (
        run_custom_checks(
            mock_entity("fluent", string="key =\n  .attr = value"),
            """key =
              { $var ->
                  [a] { "x" }
                 *[b] { "y" }
              }
              .attr = { "z" }
            """,
        )
        == {}
    )


def test_android_simple(mock_entity):
    assert run_custom_checks(mock_entity("android", string="source"), "target") == {}


def test_android_plural(mock_entity):
    assert (
        run_custom_checks(
            mock_entity(
                "android", string=".input {$n :number} .match $n one {{s1}} * {{s*}}"
            ),
            ".input {$n :number} .match $n one {{t1}} * {{t*}}",
        )
        == {}
    )

    assert run_custom_checks(
        mock_entity("android", string="source"),
        ".input {$n :number} .match $n one {{t1}} * {{t*}}",
    ) == {"pErrors": plural_error}


def test_po_newlines(mock_entity):
    assert run_custom_checks(mock_entity("gettext"), "aaa\nbbb") == {}


def test_ftl_parse_error(mock_entity):
    """Invalid FTL strings are not allowed"""
    ftl_entity = mock_entity("fluent", string="key = value")
    assert run_custom_checks(ftl_entity, "key =") == {
        "pErrors": ['Expected message "key" to have a value or attributes']
    }
    assert run_custom_checks(ftl_entity, "key = translation") == {}


def test_ftl_non_localizable_entries(mock_entity):
    """Non-localizable entries are not allowed"""
    assert run_custom_checks(
        mock_entity("fluent", string="key = value"), "[[foo]]"
    ) == {"pErrors": ["Expected an entry start"]}


def test_ftl_id_mismatch(mock_entity):
    """ID of the source string and translation must be the same"""
    assert run_custom_checks(
        mock_entity("fluent", string="key = value"), "key1 = translation"
    ) == {"pErrors": ["Translation key needs to match source string key"]}


def test_android_apostrophes(mock_entity):
    original = "Source string"
    translation = "Translation with a straight '"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_percent_signs_same(mock_entity):
    original = "Source string 100%"
    translation = "Translation string 100%"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_percent_signs_more(mock_entity):
    original = "Source string 100%"
    translation = "Translation 100%! string 100%"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_literal_newline(mock_entity):
    original = "Source string"
    translation = r"Translation with an escaped \\n newline"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_same_placeholder(mock_entity):
    original = "Source string with a {$arg1 :string @source=|%1$s|}"
    translation = "Translation with a {$arg1 :string @source=|%1$s|}"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_plural_placeholders(mock_entity):
    original = """
        .input {$n :number}
        .match $n
        one {{One item}}
        * {{{$arg1 :number @source=|%1$d|} items}}
    """
    translation = """
        .input {$n :number}
        .match $n
        one {{{$arg1 :number @source=|%1$d|} item}}
        many {{{$arg1 :number @source=|%1$d|} items}}
        * {{{$arg1 :number @source=|%1$d|} items}}
    """
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_missing_placeholder(mock_entity):
    original = "Source string with a {$arg1 :string @source=|%1$s|}"
    translation = "Translation"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pndbWarnings": ["Placeholder %1$s not found in translation"]
    }


def test_android_mistyped_placeholder(mock_entity):
    original = "Source string with a {$arg1 :string @source=|%1$s|}"
    translation = "Translation %1"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder %1 not found in reference"],
        "pndbWarnings": ["Placeholder %1$s not found in translation"],
    }


def test_android_extra_placeholder(mock_entity):
    original = "Source string"
    translation = "Translation with a {$arg1 :string @source=|%1$s|}"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder %1$s not found in reference"]
    }


def test_android_extra_placeholder_as_literal(mock_entity):
    original = "Source string"
    translation = "Translation with a %1$s"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder %1$s not found in reference"]
    }


def test_android_changed_placeholder(mock_entity):
    original = (
        "New! {$arg :string @source=|%s|} email masks are now available on mobile."
    )
    translation = "Нав! Акнун ниқобҳои почтаи электронии «{$arg1 :string @source=|%@|}» дар дастгоҳҳои мобилӣ дастрасанд."
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder %@ not found in reference"],
        "pndbWarnings": ["Placeholder %s not found in translation"],
    }


def test_android_protections(mock_entity):
    original = "Source {$string :xliff:g id=string @translate=no @source=String} with {$variable :xliff:g id=variable example=5 @translate=no @source=|%1$s|}"
    translation = "Translation String with %1$s"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pndbWarnings": ["Placeholder String not found in translation"]
    }


def test_android_good_html(mock_entity):
    original = "Source with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}"
    translation = (
        "Translation with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}"
    )
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_good_html_as_literal(mock_entity):
    original = "Source with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}"
    translation = "Translation with a <b>line<br>break</b>"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_bad_html(mock_entity):
    original = "Source {|<b>| :html}string{|</b>| :html}"
    translation = "Translation with a <a>tag mismatch{|</b>| :html}"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Element <a> not found in reference"],
        "pndbWarnings": ["Element <b> not found in translation"],
    }


def test_android_extra_percent(mock_entity):
    original = "Source percent"
    translation = "Translation {|%| @source=|%%|}"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_webext_literal_index_placeholder_as_placeholder(mock_entity):
    original = "Source string with a {$arg1 @source=|$1|}"
    translation = "Translation with a {$arg1 @source=|$1|}"
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_webext_literal_index_placeholder_as_literal(mock_entity):
    original = "Source string with a {$arg1 @source=|$1|}"
    translation = "Translation with a $1"
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_webext_literal_named_placeholder_as_placeholder(mock_entity):
    original = (
        ".local $FOO = {$arg1 @source=|$1|}\n"
        + "{{Source string with a {$FOO @source=|$FOO$|}}}"
    )
    translation = (
        ".local $FOO = {$arg1 @source=|$1|}\n"
        + "{{Translation with a {$FOO @source=|$FOO$|}}}"
    )
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_webext_literal_named_placeholder_as_literal(mock_entity):
    original = (
        ".local $FOO = {$arg1 @source=|$1|}\n"
        + "{{Source string with a {$FOO @source=|$FOO$|}}}"
    )
    translation = "Translation with a $FOO$"
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_webext_extra_index_placeholder(mock_entity):
    original = "Source string"
    translation = "Translation with a $1"
    entity = mock_entity("webext", string=original)
    # This should probably also be caught!! Eeh YES!!?!
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder $1 not found in reference"]
    }


def test_webext_extra_named_placeholder_as_literal(mock_entity):
    original = "Source string"
    translation = "Translation with a $FOO$"
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder $FOO$ not found in reference"]
    }


def test_webext_extra_named_placeholder_as_placeholder(mock_entity):
    original = "Source string"
    translation = (
        ".local $FOO = {$arg1 @source=|$1|}\n"
        + "{{Translation with a {$FOO @source=|$FOO$|}}}"
    )
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder $FOO$ not found in reference"]
    }


def test_xcode_same_placeholder(mock_entity):
    original = "Source string with a {$arg1 :string @source=|%1$@|}"
    translation = "Translation with a {$arg1 :string @source=|%1$@|}"
    entity = mock_entity("xcode", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_xcode_missing_placeholder(mock_entity):
    original = "Source string with a {$arg :string @source=|%@|}"
    translation = "Translation"
    entity = mock_entity("xcode", string=original)
    assert run_custom_checks(entity, translation) == {
        "pndbWarnings": ["Placeholder %@ not found in translation"]
    }


def test_xcode_mistyped_placeholder(mock_entity):
    original = "Source string with a {$arg :string @source=|%@|}"
    translation = "Translation % @"
    entity = mock_entity("xcode", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder % @ not found in reference"],
        "pndbWarnings": ["Placeholder %@ not found in translation"],
    }


def test_xcode_extra_placeholder(mock_entity):
    original = "Source string"
    translation = "Translation with a {$arg :string @source=|%@|}"
    entity = mock_entity("xcode", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder %@ not found in reference"]
    }
