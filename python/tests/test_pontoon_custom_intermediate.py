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
from unittest.mock import MagicMock

from fluent.syntax import FluentParser, ast
from moz.l10n.formats.mf2 import mf2_parse_message
from moz.l10n.lint import content, placeholder, structure
from moz.l10n.lint.model import Diagnostic, LintContext

ftl_parser = FluentParser()


@dataclass
class Resource:
    format: str
    path: str
    allows_empty_translations: bool = False

    class Format:
        ANDROID = "android"
        DTD = "dtd"
        FLUENT = "fluent"
        GETTEXT = "gettext"
        INI = "ini"
        PLAIN_JSON = "plain_json"
        PROPERTIES = "properties"
        WEBEXT = "webext"
        XCODE = "xcode"
        XLIFF = "xliff"


@dataclass
class Entity:
    string: str
    resource: Resource


def mock_entity(
    format: str,
    *,
    string: str = "",
    allows_empty_translations: bool = False,
):
    entity = MagicMock()
    entity.string = string
    entity.resource.format = format
    entity.resource.allows_empty_translations = allows_empty_translations
    return entity


def run_custom_checks(entity: Entity, string: str) -> dict[str, list[str]]:
    """
    Group all checks related to the base UI that get stored in the DB
    """
    context = LintContext(
        resource_format=entity.resource.format,
        allows_empty_translations=entity.resource.allows_empty_translations,
        raw_source=entity.string,
        raw_translation=string,
    )

    diagnostics: list[Diagnostic] = []
    errors: list[str] = []
    warnings: list[str] = []
    if context.is_fluent:
        msg = ftl_parser.parse_entry(string)
        orig_msg = ftl_parser.parse_entry(entity.string)

        # Parse error
        if (
            isinstance(msg, ast.Junk)
            and msg.annotations
            and msg.annotations[0].message is not None
        ):
            errors.append(msg.annotations[0].message)

    else:
        try:
            msg = mf2_parse_message(string)
        except ValueError as e:
            msg = None
            errors.append(f"Parse error: {e}")
        try:
            orig_msg = mf2_parse_message(entity.string)
        except ValueError as e:
            orig_msg = None
            warnings.append(f"Source parse error: {e}")

    for rule in (
        content.trailing_newline_mismatch,
        content.empty_translation,
        structure.message_id_mismatch,
        structure.plural_source_required,
        # structure.invalid_localizable_entry, # Untested in Pontoon's `test_custom`
        placeholder.not_in_reference,
        placeholder.not_in_translation,
        placeholder.unsupported,
    ):
        try:
            diagnostics.extend(rule.check(msg, orig_msg, context))
        except Exception as error:
            error

    errors.extend(d.message for d in diagnostics if d.severity == "error")
    warnings.extend(d.message for d in diagnostics if d.severity == "warning")
    checks: dict[str, list[str]] = {}
    if errors:
        checks["pErrors"] = errors
    if warnings:
        checks["pndbWarnings"] = warnings
    return checks


empty_error = ["Empty translations are not allowed"]
plural_error = ["Plural translation requires plural source"]


def test_ending_newline():
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


def test_empty_translations_allowed():
    """
    Empty translations should be allowed but noted for some extensions.
    """
    assert run_custom_checks(
        mock_entity("properties", allows_empty_translations=True), ""
    ) == {"pndbWarnings": ["Empty translation"]}


def test_empty_translations_not_allowed():
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


def test_android_simple():
    assert run_custom_checks(mock_entity("android", string="source"), "target") == {}


def test_android_plural():
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


def test_po_newlines():
    assert run_custom_checks(mock_entity("gettext"), "aaa\nbbb") == {}


def test_ftl_parse_error():
    """Invalid FTL strings are not allowed"""
    ftl_entity = mock_entity("fluent", string="key = value")
    assert run_custom_checks(ftl_entity, "key =") == {
        "pErrors": ['Expected message "key" to have a value or attributes']
    }
    assert run_custom_checks(ftl_entity, "key = translation") == {}


def test_ftl_non_localizable_entries():
    """Non-localizable entries are not allowed"""
    assert run_custom_checks(
        mock_entity("fluent", string="key = value"), "[[foo]]"
    ) == {"pErrors": ["Expected an entry start"]}


def test_ftl_id_mismatch():
    """ID of the source string and translation must be the same"""
    assert run_custom_checks(
        mock_entity("fluent", string="key = value"), "key1 = translation"
    ) == {"pErrors": ["Translation key needs to match source string key"]}


def test_android_apostrophes():
    original = "Source string"
    translation = "Translation with a straight '"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_percent_signs_same():
    original = "Source string 100%"
    translation = "Translation string 100%"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_percent_signs_more():
    original = "Source string 100%"
    translation = "Translation 100%! string 100%"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_literal_newline():
    original = "Source string"
    translation = r"Translation with an escaped \\n newline"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_same_placeholder():
    original = "Source string with a {$arg1 :string @source=|%1$s|}"
    translation = "Translation with a {$arg1 :string @source=|%1$s|}"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_plural_placeholders():
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


def test_android_missing_placeholder():
    original = "Source string with a {$arg1 :string @source=|%1$s|}"
    translation = "Translation"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pndbWarnings": ["Placeholder %1$s not found in translation"]
    }


def test_android_mistyped_placeholder():
    original = "Source string with a {$arg1 :string @source=|%1$s|}"
    translation = "Translation %1"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder %1 not found in reference"],
        "pndbWarnings": ["Placeholder %1$s not found in translation"],
    }


def test_android_extra_placeholder():
    original = "Source string"
    translation = "Translation with a {$arg1 :string @source=|%1$s|}"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder %1$s not found in reference"]
    }


def test_android_extra_placeholder_as_literal():
    original = "Source string"
    translation = "Translation with a %1$s"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder %1$s not found in reference"]
    }


def test_android_changed_placeholder():
    original = (
        "New! {$arg :string @source=|%s|} email masks are now available on mobile."
    )
    translation = "Нав! Акнун ниқобҳои почтаи электронии «{$arg1 :string @source=|%@|}» дар дастгоҳҳои мобилӣ дастрасанд."
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder %@ not found in reference"],
        "pndbWarnings": ["Placeholder %s not found in translation"],
    }


def test_android_protections():
    original = "Source {$string :xliff:g id=string @translate=no @source=String} with {$variable :xliff:g id=variable example=5 @translate=no @source=|%1$s|}"
    translation = "Translation String with %1$s"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pndbWarnings": ["Placeholder String not found in translation"]
    }


def test_android_good_html():
    original = "Source with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}"
    translation = (
        "Translation with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}"
    )
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_good_html_as_literal():
    original = "Source with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}"
    translation = "Translation with a <b>line<br>break</b>"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_android_bad_html():
    original = "Source {|<b>| :html}string{|</b>| :html}"
    translation = "Translation with a <a>tag mismatch{|</b>| :html}"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Element <a> not found in reference"],
        "pndbWarnings": ["Element <b> not found in translation"],
    }


def test_android_extra_percent():
    original = "Source percent"
    translation = "Translation {|%| @source=|%%|}"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_webext_literal_index_placeholder_as_placeholder():
    original = "Source string with a {$arg1 @source=|$1|}"
    translation = "Translation with a {$arg1 @source=|$1|}"
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_webext_literal_index_placeholder_as_literal():
    original = "Source string with a {$arg1 @source=|$1|}"
    translation = "Translation with a $1"
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_webext_literal_named_placeholder_as_placeholder():
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


def test_webext_literal_named_placeholder_as_literal():
    original = (
        ".local $FOO = {$arg1 @source=|$1|}\n"
        + "{{Source string with a {$FOO @source=|$FOO$|}}}"
    )
    translation = "Translation with a $FOO$"
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_webext_extra_index_placeholder():
    original = "Source string"
    translation = "Translation with a $1"
    entity = mock_entity("webext", string=original)
    # This should probably also be caught!! Eeh YES!!?!
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder $1 not found in reference"]
    }


def test_webext_extra_named_placeholder_as_literal():
    original = "Source string"
    translation = "Translation with a $FOO$"
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder $FOO$ not found in reference"]
    }


def test_webext_extra_named_placeholder_as_placeholder():
    original = "Source string"
    translation = (
        ".local $FOO = {$arg1 @source=|$1|}\n"
        + "{{Translation with a {$FOO @source=|$FOO$|}}}"
    )
    entity = mock_entity("webext", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder $FOO$ not found in reference"]
    }


def test_xcode_same_placeholder():
    original = "Source string with a {$arg1 :string @source=|%1$@|}"
    translation = "Translation with a {$arg1 :string @source=|%1$@|}"
    entity = mock_entity("xcode", string=original)
    assert run_custom_checks(entity, translation) == {}


def test_xcode_missing_placeholder():
    original = "Source string with a {$arg :string @source=|%@|}"
    translation = "Translation"
    entity = mock_entity("xcode", string=original)
    assert run_custom_checks(entity, translation) == {
        "pndbWarnings": ["Placeholder %@ not found in translation"]
    }


def test_xcode_mistyped_placeholder():
    original = "Source string with a {$arg :string @source=|%@|}"
    translation = "Translation % @"
    entity = mock_entity("xcode", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder % @ not found in reference"],
        "pndbWarnings": ["Placeholder %@ not found in translation"],
    }


def test_xcode_extra_placeholder():
    original = "Source string"
    translation = "Translation with a {$arg :string @source=|%@|}"
    entity = mock_entity("xcode", string=original)
    assert run_custom_checks(entity, translation) == {
        "pErrors": ["Placeholder %@ not found in reference"]
    }
