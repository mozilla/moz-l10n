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

import dataclasses
from typing import Any

import pytest
from moz.l10n.formats import Format
from moz.l10n.formats.mf2 import mf2_parse_message
from moz.l10n.lint import placeholder
from moz.l10n.lint.model import Diagnostic, LintContext, Severity
from moz.l10n.model import Expression, VariableRef

PLACEHOLDER_CHECKS = {
    "extra": placeholder.ExtraPlaceholder(),
    "missing": placeholder.MissingPlaceholder(),
    "extra-element": placeholder.ExtraElement(),
    "missing-element": placeholder.MissingElement(),
}


def _check_all_placeholder_rules(
    target_raw: str, source_raw: str, format: Format = Format.android
) -> list[dict[str, Any]]:
    """Parse incoming strings via MF2, run rules under the given format context,
    and gather diagnostics from all checks.
    """
    target = mf2_parse_message(target_raw)
    source = mf2_parse_message(source_raw)
    context = LintContext(format)
    diagnostics: list[Diagnostic] = []
    for rule in PLACEHOLDER_CHECKS.values():
        diagnostics.extend(rule.check(target, source, context))
    return [dataclasses.asdict(d) for d in diagnostics]


class TestBasic:
    """Basic Presence Checks (Same, Missing, Extra, Mistyped)"""

    def test_android_same_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a {$arg1 :string @source=|%1$s|}",
            "Source string with a {$arg1 :string @source=|%1$s|}",
            Format.android,
        )
        assert result == []

    def test_android_missing_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation",
            "Source string with a {$arg1 :string @source=|%1$s|}",
            Format.android,
        )
        assert result == [
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder %1$s not found in translation",
                "severity": Severity.WARNING,
            }
        ]

    def test_android_mistyped_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation  {$arg1 :string @source=|%1|}",
            "Source string with a {$arg1 :string @source=|%1$s|}",
            Format.android,
        )
        assert result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": "Placeholder %1 not found in reference",
                "severity": Severity.ERROR,
            },
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder %1$s not found in translation",
                "severity": Severity.WARNING,
            },
        ]

    def test_android_extra_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a {$arg1 :string @source=|%1$s|}",
            "Source string",
            Format.android,
        )
        assert result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": "Placeholder %1$s not found in reference",
                "severity": Severity.ERROR,
            }
        ]

    def test_android_changed_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            "Нав! Акнун ниқобҳои почтаи электронии «{$arg1 :string @source=|%@|}» дар дастгоҳҳои мобилӣ дастрасанд.",
            "New! {$arg :string @source=|%s|} email masks are now available on mobile.",
            Format.android,
        )
        assert result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": "Placeholder %@ not found in reference",
                "severity": Severity.ERROR,
            },
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder %s not found in translation",
                "severity": Severity.WARNING,
            },
        ]

    def test_extra_percent_escapes_ignored(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation {|%| @source=|%%|}",
            "Source percent",
            Format.android,
        )
        assert result == []

    def test_mf2_plain_variable_placeholder(self) -> None:
        """Covers Expression nodes with a VariableRef argument (e.g. {$user})."""
        result = _check_all_placeholder_rules(
            "Hello {$user}",
            "Source {$user}",
            Format.mf2,
        )
        assert result == []

        missing_result = _check_all_placeholder_rules(
            "Hello",
            "Source {$user}",
            Format.mf2,
        )
        assert missing_result == [
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder $user not found in translation",
                "severity": Severity.WARNING,
            }
        ]

    def test_mf2_entity_placeholder(self) -> None:
        """Covers Expression nodes with :entity function."""
        result = _check_all_placeholder_rules(
            "Welcome to {$brand :entity}",
            "Source {$brand :entity}",
            Format.mf2,
        )
        assert result == []

        missing_result = _check_all_placeholder_rules(
            "Welcome",
            "Source {$brand :entity}",
            Format.mf2,
        )
        assert missing_result == [
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder brand not found in translation",
                "severity": Severity.WARNING,
            }
        ]

    def test_mf2_literal_expression_placeholder(self) -> None:
        """Covers Expression nodes with literal arguments (e.g. {|42|})."""
        result = _check_all_placeholder_rules(
            "Count: {|42|}",
            "Source: {|42|}",
            Format.mf2,
        )
        assert result == []

        missing_result = _check_all_placeholder_rules(
            "Count",
            "Source: {|42|}",
            Format.mf2,
        )
        assert missing_result == [
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder 42 not found in translation",
                "severity": Severity.WARNING,
            }
        ]


class TestPlainText:
    """Plain Text Safety & Escaping (Apostrophes, Newlines, Literal Percents)"""

    def test_android_apostrophes(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a straight '",
            "Source string",
            Format.android,
        )
        assert result == []

    def test_android_percent_signs_same(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation string 100%",
            "Source string 100%",
            Format.android,
        )
        assert result == []

    def test_android_percent_signs_more(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation 100%! string 100%",
            "Source string 100%",
            Format.android,
        )
        assert result == []

    def test_android_literal_newline(self) -> None:
        result = _check_all_placeholder_rules(
            r"Translation with an escaped \\n newline",
            "Source string",
            Format.android,
        )
        assert result == []


class TestCounts:
    """Unnumbered vs. Reusable Placeholder Occurrence Counting."""

    @pytest.mark.parametrize(
        "format, placeholder",
        [
            (Format.xliff, "%@"),
            (Format.android, "%s"),
            (Format.android, "%02d"),
            (Format.xliff, "%#x"),
        ],
    )
    @pytest.mark.parametrize("count", [0, 1, 2])
    def test_repeated_unnumbered_placeholder(
        self, format: Format, placeholder: str, count: int
    ) -> None:
        first = f"{{$arg1 :string @source=|{placeholder}|}}"
        second = f"{{$arg2 :string @source=|{placeholder}|}}"
        translation = "Hello " + " and ".join([first, second][:count])
        result = _check_all_placeholder_rules(
            translation, f"Hello {first} and {second}", format
        )

        expected = []
        if count == 0:
            expected = [
                {
                    "rule_name": "missing",
                    "rule_family": "placeholder",
                    "message": f"Placeholder {placeholder} not found in translation",
                    "severity": Severity.WARNING,
                }
            ]
        elif count == 1:
            expected = [
                {
                    "rule_name": "missing",
                    "rule_family": "placeholder",
                    "message": (
                        f"Placeholder {placeholder} has fewer occurrences in translation "
                        "(expected 2, found 1)"
                    ),
                    "severity": Severity.WARNING,
                }
            ]
        assert result == expected

    def test_repeated_unnumbered_placeholder_extra_occurrence(self) -> None:
        first = "{$arg1 :string @source=|%@|}"
        second = "{$arg2 :string @source=|%@|}"
        third = "{$arg3 :string @source=|%@|}"
        result = _check_all_placeholder_rules(
            f"Hello {first}, {second} and {third}",
            f"Hello {first} and {second}",
            Format.xliff,
        )
        assert result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": "Placeholder %@ has more occurrences in translation (expected 2, found 3)",
                "severity": Severity.ERROR,
            }
        ]

    @pytest.mark.parametrize(
        "format, placeholder",
        [
            (Format.xliff, "%1$@"),
            (Format.android, "%1$s"),
            (Format.xliff, "%#@items@"),
        ],
    )
    def test_repeated_reusable_placeholder(
        self, format: Format, placeholder: str
    ) -> None:
        arg = f"{{$arg1 :string @source=|{placeholder}|}}"
        result = _check_all_placeholder_rules(
            f"Hello {arg}",
            f"Hello {arg} and {arg}",
            format,
        )
        assert result == []

    @pytest.mark.parametrize("source_count, target_count", [(2, 1), (1, 2), (2, 2)])
    def test_repeated_element_with_unnumbered_placeholder(
        self, source_count: int, target_count: int
    ) -> None:
        element = '<a href="{$arg1 :string @source=|%@|}">link</a>'
        source = " ".join([element] * source_count)
        target = " ".join([element] * target_count)
        result = _check_all_placeholder_rules(target, source, Format.xliff)

        expected = []
        if source_count != target_count:
            fewer = target_count < source_count
            direction = "fewer" if fewer else "more"
            rule_name = "missing" if fewer else "extra"
            severity = Severity.WARNING if fewer else Severity.ERROR
            expected = [
                {
                    "rule_name": rule_name,
                    "rule_family": "placeholder",
                    "message": (
                        f"Placeholder %@ has {direction} occurrences in translation "
                        f"(expected {source_count}, found {target_count})"
                    ),
                    "severity": severity,
                }
            ]
        assert result == expected


class TestPluralVariants:
    """Plural Variants & Asymmetric Counts"""

    @pytest.mark.parametrize("missing", [False, True])
    def test_repeated_unnumbered_placeholder_plural_variants(
        self, missing: bool
    ) -> None:
        first = "{$arg1 :string @source=|%s|}"
        second = "{$arg2 :string @source=|%s|}"
        original = (
            ".input {$n :number} .match $n "
            f"one {{{{For {first} and {second}}}}} "
            f"* {{{{For {first} and {second}}}}}"
        )
        pattern = first if missing else f"{first} and {second}"
        translation = (
            ".input {$n :number} .match $n "
            f"one {{{{For {pattern}}}}} "
            f"few {{{{For {pattern}}}}} "
            f"* {{{{For {pattern}}}}}"
        )
        result = _check_all_placeholder_rules(translation, original, Format.android)
        expected = (
            [
                {
                    "rule_name": "missing",
                    "rule_family": "placeholder",
                    "message": "Placeholder %s has fewer occurrences in translation (expected 2, found 1)",
                    "severity": Severity.WARNING,
                }
            ]
            if missing
            else []
        )
        assert result == expected

    def test_repeated_unnumbered_placeholder_fewer_source_variants(self) -> None:
        first = "{$arg1 :string @source=|%s|}"
        second = "{$arg2 :string @source=|%s|}"
        original = (
            ".input {$n :number} .match $n "
            f"one {{{{ {first} of {second} }}}} "
            f"* {{{{ {first} items }}}}"
        )
        translation = f".input {{$n :number}} .match $n * {{{{ {first} items }}}}"
        result = _check_all_placeholder_rules(translation, original, Format.android)
        assert result == []

    @pytest.mark.parametrize("count", [1, 3])
    def test_unnumbered_placeholder_mismatch_in_one_plural_variant(
        self, count: int
    ) -> None:
        arg = "{$arg1 :string @source=|%@|}"
        pair = f"{arg} {arg}"
        original = (
            f".input {{$n :number}} .match $n one {{{{ {pair} }}}} * {{{{ {pair} }}}}"
        )
        changed = " ".join([arg] * count)
        translation = f".input {{$n :number}} .match $n one {{{{ {changed} }}}} * {{{{ {pair} }}}}"

        result = _check_all_placeholder_rules(translation, original, Format.xliff)
        direction = "fewer" if count == 1 else "more"
        rule_name = "missing" if count == 1 else "extra"
        severity = Severity.WARNING if count == 1 else Severity.ERROR

        assert result == [
            {
                "rule_name": rule_name,
                "rule_family": "placeholder",
                "message": f"Placeholder %@ has {direction} occurrences in translation (expected 2, found {count})",
                "severity": severity,
            }
        ]

    def test_missing_elements_in_different_source_variants(self) -> None:
        original = (
            ".input {$n :number} .match $n "
            "one {{{#a href=|%@|}link{/a}}} "
            "* {{{#a title=|%@|}link{/a}}}"
        )
        translation = ".input {$n :number} .match $n * {{link{/a}}}"
        result = _check_all_placeholder_rules(translation, original, Format.xliff)

        assert result == [
            {
                "rule_name": "missing-element",
                "rule_family": "placeholder",
                "message": 'Element <a href="%@"> not found in translation',
                "severity": Severity.WARNING,
            },
            {
                "rule_name": "missing-element",
                "rule_family": "placeholder",
                "message": 'Element <a title="%@"> not found in translation',
                "severity": Severity.WARNING,
            },
        ]


class TestMarkup:
    """Markup, Literal Angle Brackets & Heuristics"""

    def test_good_html(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}",
            "Source with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}",
        )
        assert result == []

    def test_android_good_html(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}",
            "Source with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}",
        )
        assert result == []

    def test_android_good_html_as_markup(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a {#b}line{#br}{/br}break{/b}",
            "Source with a {#b}line{#br}{/br}break{/b}",
        )
        assert result == []

    def test_android_bad_html(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a {|<a>| :html}tag mismatch{|</b>| :html}",
            "Source {|<b>| :html}string{|</b>| :html}",
        )
        assert result == [
            {
                "rule_name": "extra-element",
                "rule_family": "placeholder",
                "message": "Element <a> not found in reference",
                "severity": Severity.ERROR,
            },
            {
                "rule_name": "missing-element",
                "rule_family": "placeholder",
                "message": "Element <b> not found in translation",
                "severity": Severity.WARNING,
            },
        ]

    def test_literal_angle_brackets_not_element(self) -> None:
        result = _check_all_placeholder_rules(
            "Premi {|<Invio>| :html} per continuare",
            "Press {|<Enter>| :html} to continue",
        )
        assert result == []

    def test_bare_element_name_not_element(self) -> None:
        result = _check_all_placeholder_rules(
            "Digita per andare a capo",
            "Type {|<br>| :html} for a break",
        )
        assert result == []

    def test_escaped_custom_element_pair(self) -> None:
        result = _check_all_placeholder_rules(
            "testo",
            "{|<myTag>| :html}text{|</myTag>| :html}",
        )
        assert result == [
            {
                "rule_name": "missing-element",
                "rule_family": "placeholder",
                "message": "Element </myTag> not found in translation",
                "severity": Severity.WARNING,
            },
            {
                "rule_name": "missing-element",
                "rule_family": "placeholder",
                "message": "Element <myTag> not found in translation",
                "severity": Severity.WARNING,
            },
        ]

    def test_escaped_element_with_attributes(self) -> None:
        result = _check_all_placeholder_rules(
            "testo",
            '{|<myTag id="1">| :html}text{|</myTag>| :html}',
        )
        assert result == [
            {
                "rule_name": "missing-element",
                "rule_family": "placeholder",
                "message": "Element </myTag> not found in translation",
                "severity": Severity.WARNING,
            },
            {
                "rule_name": "missing-element",
                "rule_family": "placeholder",
                "message": 'Element <myTag id="1"> not found in translation',
                "severity": Severity.WARNING,
            },
        ]

    def test_stray_angle_brackets_ignored(self) -> None:
        result = _check_all_placeholder_rules(
            "5 {|< 10 e x >| :html} y",
            "5 {|< 10 and x >| :html} y",
        )
        assert result == []

    def test_equal_links(self) -> None:
        result = _check_all_placeholder_rules(
            "{#a href=$url}link{/a}", "{#a href=$url}link{/a}"
        )
        assert result == []

    def test_mf2_function_markup(self) -> None:
        """Check Expression without string or VariableRef arg, e.g. function call with no args."""
        result1 = _check_all_placeholder_rules(
            "Hola {:current_date}", "Hello {:current_date}"
        )
        assert result1 == []


class TestAttributes:
    """Placeholders in Attributes & Suppression Cascades"""

    def test_placeholder_in_element(self) -> None:
        original = (
            'Read the <a href="{$arg1 :string @source=|%1$s|}">policy{|</a>| :html}'
        )
        result = _check_all_placeholder_rules(original, original, Format.android)
        assert result == []

    @pytest.mark.parametrize(
        "format, placeholder",
        [(Format.xliff, "%1$@"), (Format.android, "%1$s")],
    )
    def test_changed_placeholder_in_element(
        self, format: Format, placeholder: str
    ) -> None:
        expected = [
            {
                "rule_name": "extra-element",
                "rule_family": "placeholder",
                "message": 'Element <a href="https://example.com"> not found in reference',
                "severity": Severity.ERROR,
            },
            {
                "rule_name": "missing-element",
                "rule_family": "placeholder",
                "message": f'Element <a href="{placeholder}"> not found in translation',
                "severity": Severity.WARNING,
            },
        ]
        result = _check_all_placeholder_rules(
            "Leggi la {#a href=|https://example.com|}policy{/a}",
            f"Read the {{#a href=|{placeholder}|}}policy{{/a}}",
            format,
        )
        assert result == expected
        result = _check_all_placeholder_rules(
            'Leggi la {|<a href="https://example.com">| :html}policy{|</a>| :html}',
            f'Read the {{|<a href="{placeholder}">| :html}}policy{{|</a>| :html}}',
            format,
        )
        assert result == expected

    def test_missing_element_suppresses_unnumbered_placeholder_warning(self) -> None:
        expected = {
            "rule_name": "missing-element",
            "rule_family": "placeholder",
            "message": 'Element <a href="%@"> not found in translation',
            "severity": Severity.WARNING,
        }
        result = _check_all_placeholder_rules(
            "Read link{|</a>| :html}",
            'Read {|<a href="%@">| :html}link{|</a>| :html}',
            Format.xliff,
        )
        assert result == [expected]

        result = _check_all_placeholder_rules(
            "Read link{/a}",
            "Read {#a href=|%@|}link{/a}",
            Format.xliff,
        )
        assert result == [expected]

    def test_extra_unnumbered_placeholder_with_markup_attribute(self) -> None:
        translation = "Hi {$arg :string @source=|%s|} {$arg2 :string @source=|%s|} {#a href=|%s|}link{/a}"
        original = "Hi {$arg :string @source=|%s|} {#a href=|%s|}link{/a}"
        result = _check_all_placeholder_rules(translation, original, Format.android)
        assert result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": "Placeholder %s has more occurrences in translation (expected 2, found 3)",
                "severity": Severity.ERROR,
            }
        ]


class TestProtections:
    """Protections & Multi-digit Placeholders"""

    def test_protections_with_shared_substring(self) -> None:
        original = (
            "Hi {$a :xliff:g id=a @translate=no @source=Name} "
            "and {$b :xliff:g id=b @translate=no @source=FullName}"
        )
        result = _check_all_placeholder_rules("Salve", original, Format.android)
        assert result == [
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder FullName not found in translation",
                "severity": Severity.WARNING,
            },
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder Name not found in translation",
                "severity": Severity.WARNING,
            },
        ]

    def test_multi_digit_placeholder_same(self) -> None:
        original = "Hi {$a :string @source=|%10$s|} and {$b :string @source=|%2$s|}"
        result = _check_all_placeholder_rules(original, original, Format.android)
        assert result == []

    def test_multi_digit_placeholder_changed(self) -> None:
        original = "Hi {$a :string @source=|%10$s|} and {$b :string @source=|%2$s|}"
        translation = "Ciao {$a :string @source=|%11$s|} e {$b :string @source=|%2$s|}"
        result = _check_all_placeholder_rules(translation, original, Format.android)
        assert result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": "Placeholder %11$s not found in reference",
                "severity": Severity.ERROR,
            },
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder %10$s not found in translation",
                "severity": Severity.WARNING,
            },
        ]


class TestWebExtension:
    """WebExtension Syntax ($1, $FOO$)"""

    def test_webext_literal_index_placeholder_as_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a {$arg1 @source=|$1|}",
            "Source string with a {$arg1 @source=|$1|}",
            Format.webext,
        )
        assert result == []

    def test_webext_literal_index_placeholder_as_literal(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a $1",
            "Source string with a {$arg1 @source=|$1|}",
            Format.webext,
        )
        assert result == [
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder $1 not found in translation",
                "severity": Severity.WARNING,
            }
        ]

    def test_webext_extra_named_placeholder_as_literal(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a {$arg @source=|$FOO$|}",
            "Source string",
            Format.webext,
        )
        assert result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": "Placeholder $FOO$ not found in reference",
                "severity": Severity.ERROR,
            }
        ]

    def test_webext_literal_named_placeholder_as_placeholder(self) -> None:
        msg = ".local $FOO = {$arg1 @source=|$1|}\n{{Translation with a {$FOO @source=|$FOO$|}}}"
        result = _check_all_placeholder_rules(msg, msg, Format.webext)
        assert result == []

    def test_webext_extra_index_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            "Translation with a $1", "Source string", Format.webext
        )
        # This should totally not be caught
        assert result == []


class TestRest:
    def test_coverage_html_markup_key(self) -> None:
        from moz.l10n.lint.placeholder.mismatch import _MarkupKey

        for arg in (VariableRef("div"), "not-a-tag", "<>", "<", ">"):
            assert (
                _MarkupKey.from_expression(Expression(function="html", arg=arg)) is None
            )
