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

from dataclasses import dataclass
from typing import Callable, Iterator
from unittest.mock import MagicMock

from moz.l10n.formats import Format, fluent, mf2
from moz.l10n.lint import content, structure
from moz.l10n.lint.model import Diagnostic, LintContext, Severity
from moz.l10n.model import Entry, Message, PatternMessage, SelectMessage

RULES = (
    content.LeadingWhitespaceMismatch(),
    content.TrailingWhitespaceMismatch(),
    content.EmptyTranslation(),
    structure.PluralSourceRequired(),
)


@dataclass
class Resource:
    format: str
    path: str
    allows_empty_translations: bool = False


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
        resource_format=Format[entity.resource.format]
        if entity.resource.format != "xcode"
        else Format.xliff
    )
    if entity.resource.allows_empty_translations:
        context.severity["content.empty-translation"] = Severity.WARNING

    target, source, warnings, errors = _parse_custom(
        string, entity.string, context.resource_format
    )
    if not errors:
        diagnostics: list[Diagnostic] = []
        for rule in RULES:
            for msg, orig_msg, _attr_key in _iter_target_source(target, source):
                diagnostics.extend(rule.check(msg, orig_msg, context))

        errors.extend(d.message for d in diagnostics if d.severity == "error")
        warnings.extend(d.message for d in diagnostics if d.severity == "warning")

    return {k: v for k, v in (("pErrors", errors), ("pndbWarnings", warnings)) if v}


empty_error = ["Empty translations are not allowed"]
empty_warning = "Empty translation"
plural_error = ["Plural translation requires plural source"]


class TestWhitespace:
    def test_ending_newline(self):
        """
        Original and translation in a PO file must either both end
        in a newline, or none of them should.
        """
        po_entity = mock_entity("gettext", string="Original")
        assert run_custom_checks(po_entity, "Translation\n") == {
            "pErrors": ["Trailing whitespace mismatch (expected '\\n', got '')"]
        }
        assert run_custom_checks(po_entity, "Translation") == {}

        po_entity.string = "Original\n"
        assert run_custom_checks(po_entity, "Translation") == {
            "pErrors": ["Trailing whitespace mismatch (expected '', got '\\n')"]
        }
        assert run_custom_checks(po_entity, "Translation\n") == {}

    def test_po_newlines(self):
        assert run_custom_checks(mock_entity("gettext"), "aaa\nbbb") == {}

    def test_android_literal_newline(self):
        original = "Source string"
        translation = r"Translation with an escaped \\n newline"
        entity = mock_entity("android", string=original)
        assert run_custom_checks(entity, translation) == {}


class TestEmpty:
    def test_empty_translations_allowed(self):
        """
        Empty translations should be allowed but noted for some extensions.
        """
        assert run_custom_checks(
            mock_entity("properties", allows_empty_translations=True), ""
        ) == {"pndbWarnings": [empty_warning]}

    def test_empty_translations_not_allowed(self):
        """
        Empty translations shouldn't be allowed for some extensions.
        """
        po_entity = mock_entity("gettext", string=" ")
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
            mock_entity("fluent", string="key = value", allows_empty_translations=True),
            'key = { "" }',
        ) == {"pndbWarnings": [empty_warning]}

        assert (
            run_custom_checks(
                mock_entity("fluent", string="key = value"), 'key = { "x" }'
            )
            == {}
        )

        assert run_custom_checks(
            mock_entity(
                "fluent",
                string="key =\n  .attr = value",
                allows_empty_translations=True,
            ),
            """key =
                { $var ->
                    [a] { "" }
                    *[b] { "" }
                }
                .attr = { "" }
                """,
        ) == {"pndbWarnings": [empty_warning, empty_warning]}

        assert run_custom_checks(
            mock_entity(
                "fluent",
                string="key =\n  .attr = value",
                allows_empty_translations=True,
            ),
            """key =
                { $var ->
                    [a] { "x" }
                    *[b] { "y" }
                }
                .attr = { "" }
                """,
        ) == {"pndbWarnings": [empty_warning]}

        assert run_custom_checks(
            mock_entity(
                "fluent",
                string="key =\n  .attr = value",
                allows_empty_translations=True,
            ),
            """key =
                { $var ->
                    [a] { "x" }
                    *[b] { "" }
                }
                .attr = { "y" }
                """,
        ) == {"pndbWarnings": [empty_warning]}

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


def test_ftl_parse_error():
    """Invalid FTL strings are not allowed"""
    ftl_entity = mock_entity("fluent", string="key = value")
    assert run_custom_checks(ftl_entity, "key =") == {
        "pErrors": ['Parse error: Expected message "key" to have a value or attributes']
    }
    assert run_custom_checks(ftl_entity, "key = translation") == {}


def test_ftl_non_localizable_entries():
    """Non-localizable entries are not allowed"""
    assert run_custom_checks(
        mock_entity("fluent", string="key = value"), "[[foo]]"
    ) == {"pErrors": ["Parse error: Expected an entry start"]}


def test_android_apostrophes():
    original = "Source string"
    translation = "Translation with a straight '"
    entity = mock_entity("android", string=original)
    assert run_custom_checks(entity, translation) == {}


def _parse_custom(
    raw_target: str,
    raw_source: str,
    resource_format: Format,
) -> tuple[Entry | Message | None, Entry | Message | None, list[str], list[str]]:
    """Parse raw inputs according to `resource_format`.
    Get `Entry` from fluent and `Message` from others.
    """
    errors: list[str] = []
    warnings: list[str] = []

    def catch_parse(
        raw_string: str, parse_func: Callable, collection: list, label: str
    ) -> Entry | Message | None:
        try:
            result = parse_func(raw_string)
        except ValueError as error:
            collection.append(f"{label} error: {error}")
            result = None
        return result

    if resource_format is Format.fluent:

        def ftl_parse(raw_string) -> Entry:
            return next(fluent.fluent_parse(raw_string).all_entries())

        target = catch_parse(raw_target, ftl_parse, errors, "Parse")
        source = catch_parse(raw_source, ftl_parse, warnings, "Source parse")
    else:
        target = catch_parse(raw_target, mf2.mf2_parse_message, errors, "Parse")
        source = catch_parse(
            raw_source, mf2.mf2_parse_message, warnings, "Source parse"
        )

    return target, source, warnings, errors


def _iter_target_source(
    target: Entry | Message | None, source: Entry | Message | None
) -> Iterator[tuple[Message | None, Message | None, str | None]]:
    """Yield tuples of Message from Message or Entry pairs.
    We have fluent examples like `key = something` which is more than a `Message`!
    Messages don't have `id`.
    """
    message_types = PatternMessage, SelectMessage
    if isinstance(target, message_types) and isinstance(source, message_types):
        yield target, source, None
        return

    trg_val = target.value if isinstance(target, Entry) else None
    src_val = source.value if isinstance(source, Entry) else None
    if trg_val is not None or src_val is not None:
        yield trg_val, src_val, None

    trg_props = target.properties if isinstance(target, Entry) else {}
    src_props = source.properties if isinstance(source, Entry) else {}
    for attr_key in dict.fromkeys(list(trg_props) + list(src_props)):
        yield (trg_props.get(attr_key), src_props.get(attr_key), attr_key)
