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
from moz.l10n.message import parse_message
from moz.l10n.model import Expression, Message, PatternMessage, VariableRef

PLACEHOLDER_CHECKS = {
    "extra": placeholder.ExtraPlaceholder(),
    "missing": placeholder.MissingPlaceholder(),
    "extra-element": placeholder.ExtraElement(),
    "missing-element": placeholder.MissingElement(),
}


def _check_all_placeholder_rules(
    source_raw: str,
    target_raw: str,
    format: Format,
    xliff_is_xcode: bool = False,
) -> list[dict[str, Any]]:
    """Parse incoming strings with their dedicated format parser,
    run rules with given format context, and gather diagnostics from all checks.
    """
    if format in (Format.android, Format.xliff):
        pytest.importorskip("lxml")
    target = parse_message(format, target_raw, xliff_is_xcode=xliff_is_xcode)
    source = parse_message(format, source_raw, xliff_is_xcode=xliff_is_xcode)
    return _call_checks(target, source, format)


def _check_all_placeholder_rules_mf2(
    source_raw: str,
    target_raw: str,
    format: Format = Format.android,
    xliff_is_xcode: bool = False,
) -> list[dict[str, Any]]:
    """Parse incoming strings via MF2 to make sure we create the desired Message objects we want to test for
    run rules with given format context, and gather diagnostics from all checks.
    """
    target = mf2_parse_message(target_raw)
    source = mf2_parse_message(source_raw)
    return _call_checks(target, source, format)


def _call_checks(
    target: Message, source: Message, format: Format
) -> list[dict[str, Any]]:
    context = LintContext(format)
    diagnostics: list[Diagnostic] = []
    for rule in PLACEHOLDER_CHECKS.values():
        diagnostics.extend(rule.check(target, source, context))
    return [dataclasses.asdict(d) for d in diagnostics]


class TestBasic:
    """Basic Presence Checks (Same, Missing, Extra, Mistyped)"""

    def test_android_same_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            "Source string with a %1$s",
            "Translation with a %1$s",
            Format.android,
        )
        assert result == []

    def test_android_missing_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            "Source string with a %1$s",
            "Translation",
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
        expected = [
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
        result = _check_all_placeholder_rules(
            "Source string with a %1$s",
            "Translation \u0020%1",
            Format.android,
        )
        assert result == expected
        result = _check_all_placeholder_rules_mf2(
            "Source string with a {$arg1 :string @source=|%1$s|}",
            "Translation  {$arg1 :string @source=|%1|}",
            Format.android,
        )
        assert result == expected

    def test_android_extra_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            "Source string",
            "Translation with a %1$s",
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
            "New! %s email masks are now available on mobile.",
            "Нав! Акнун ниқобҳои почтаи электронии «%@» дар дастгоҳҳои мобилӣ дастрасанд.",
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
            "Translation %%",
            "Source percent",
            Format.android,
        )
        assert result == []
        result = _check_all_placeholder_rules_mf2(
            "Translation {|%| @source=|%%|}",
            "Source percent",
            Format.android,
        )
        assert result == []

    def test_mf2_plain_variable_placeholder(self) -> None:
        """Covers Expression nodes with a VariableRef argument (e.g. {$user})."""
        result = _check_all_placeholder_rules(
            "Source {$user}", "Hello {$user}", Format.mf2
        )
        assert result == []

        missing_result = _check_all_placeholder_rules(
            "Source {$user}", "Hello", Format.mf2
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
            "Source {$brand :entity}", "Welcome", Format.mf2
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
        """Check Expression nodes with literal arguments (e.g. `{42}`, `{|42|}`)."""
        result = _check_all_placeholder_rules("Source: {42}", "Count: {42}", Format.mf2)
        assert result == []
        result = _check_all_placeholder_rules(
            "Source: {|42|}", "Count: {|42|}", Format.mf2
        )
        assert result == []

        missing_result = _check_all_placeholder_rules(
            "Source: {42}", "Count", Format.mf2
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
            "Source string 100%", "Translation string 100%", Format.android
        )
        assert result == []

    def test_android_percent_signs_more(self) -> None:
        """"""
        result = _check_all_placeholder_rules_mf2(
            "Source string 100%", "Translation 100%! string 100%", Format.android
        )
        assert result == []

        result = _check_all_placeholder_rules(
            "Source string 100%", "Translation 100%! string 100%", Format.android
        )
        assert result == [
            {
                "message": "Placeholder %! not found in reference",
                "rule_family": "placeholder",
                "rule_name": "extra",
                "severity": Severity.ERROR,
            }
        ]

    def test_android_literal_newline(self) -> None:
        result = _check_all_placeholder_rules(
            "Source string", r"Translation with an escaped \\n newline", Format.android
        )
        assert result == []


class TestCounts:
    """Unnumbered vs. Reusable Placeholder Occurrence Counting."""

    @pytest.mark.parametrize(
        "format, placeholder",
        [
            (Format.xliff, "%@"),
            (Format.xliff, "%#x"),
            (Format.android, "%s"),
            (Format.android, "%02d"),
        ],
    )
    @pytest.mark.parametrize("count", [0, 1, 2])
    def test_repeated_unnumbered_placeholder(
        self, format: Format, placeholder: str, count: int
    ) -> None:
        result = _check_all_placeholder_rules(
            f"Hello {placeholder} and {placeholder}",
            "Hello " + " and ".join([placeholder, placeholder][:count]),
            format,
            xliff_is_xcode=True,
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
        result = _check_all_placeholder_rules(
            "Hello %@ and %@",
            "Hello %@, %@ and %@",
            Format.xliff,
            xliff_is_xcode=True,
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
            f"Hello {arg} and {arg}",
            f"Hello {arg}",
            format,
            xliff_is_xcode=True,
        )
        assert result == []

    @pytest.mark.parametrize("source_count, target_count", [(2, 1), (1, 2), (2, 2)])
    def test_repeated_element_with_unnumbered_placeholder(
        self, source_count: int, target_count: int
    ) -> None:
        element = '<a href="%@">link</a>'
        source = " ".join([element] * source_count)
        target = " ".join([element] * target_count)
        result = _check_all_placeholder_rules(source, target, Format.xliff)
        expected = []
        if source_count != target_count:
            fewer = target_count < source_count
            direction = "fewer" if fewer else "more"
            expected.append(
                {
                    "rule_name": "missing" if fewer else "extra",
                    "rule_family": "placeholder",
                    "message": (
                        f"Placeholder %@ has {direction} occurrences in translation "
                        f"(expected {source_count}, found {target_count})"
                    ),
                    "severity": Severity.WARNING if fewer else Severity.ERROR,
                }
            )
        assert result == expected


class TestPluralVariants:
    """Plural Variants & Asymmetric Counts"""

    @pytest.mark.parametrize("missing", [False, True])
    def test_repeated_unnumbered_placeholder_plural_variants(
        self, missing: bool
    ) -> None:
        """Using mf2 parser. Using android parser produces error:
        `Unsupported message: SelectMessage(...`

        """
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
        result = _check_all_placeholder_rules_mf2(original, translation)
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
        """Using mf2 parser. Trying with android parser produced an error:
        `Unsupported message: SelectMessage(declarations={'n': Expression(VariableRef...`
        """
        first = "{$arg1 :string @source=|%s|}"
        second = "{$arg2 :string @source=|%s|}"
        original = (
            ".input {$n :number} .match $n "
            f"one {{{{ {first} of {second} }}}} "
            f"* {{{{ {first} items }}}}"
        )
        translation = f".input {{$n :number}} .match $n * {{{{ {first} items }}}}"
        result = _check_all_placeholder_rules_mf2(original, translation, Format.android)
        assert result == []

    @pytest.mark.parametrize("count", [1, 3])
    def test_unnumbered_placeholder_mismatch_in_one_plural_variant(
        self, count: int
    ) -> None:
        """Using mf2 parser. Trying with xliff parser produced an error:
        `Unsupported message: SelectMessage(declarations={'n': Expression...`
        """
        arg = "{$arg1 :string @source=|%@|}"
        pair = f"{arg} {arg}"
        original = (
            f".input {{$n :number}} .match $n one {{{{ {pair} }}}} * {{{{ {pair} }}}}"
        )
        changed = " ".join([arg] * count)
        translation = f".input {{$n :number}} .match $n one {{{{ {changed} }}}} * {{{{ {pair} }}}}"

        result = _check_all_placeholder_rules_mf2(original, translation, Format.xliff)
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
        """Using mf2 parser. Trying with xliff parser produced an error:
        `Unsupported message: SelectMessage(declarations={'n': ...`
        """
        original = (
            ".input {$n :number} .match $n "
            "one {{{#a href=|%@|}link{/a}}} "
            "* {{{#a title=|%@|}link{/a}}}"
        )
        translation = ".input {$n :number} .match $n * {{link{/a}}}"
        result = _check_all_placeholder_rules_mf2(original, translation, Format.xliff)
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
            "Source with a &lt;b&gt;line&lt;br&gt;break&lt;/b&gt;",
            "Translation with a &lt;b&gt;line&lt;br&gt;break&lt;/b&gt;",
            Format.android,
        )
        assert result == []
        result = _check_all_placeholder_rules_mf2(
            "Source with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}",
            "Translation with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}",
            Format.android,
        )
        assert result == []

    def test_android_good_html(self) -> None:
        result = _check_all_placeholder_rules(
            "Source with a &lt;b&gt;line&lt;br&gt;break&lt;/b&gt;",
            "Translation with a &lt;b&gt;line&lt;br&gt;break&lt;/b&gt;",
            Format.android,
        )
        assert result == []
        result = _check_all_placeholder_rules_mf2(
            "Source with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}",
            "Translation with a {|<b>| :html}line{|<br>| :html}break{|</b>| :html}",
            Format.android,
        )
        assert result == []

    def test_android_good_html_as_markup(self) -> None:
        """Using mf2 parser. Trying with android parser produced an error:
        `Opening and ending tag mismatch: br line 1 and b, line 1, column 48 (<string>, line 1)`
        """
        result = _check_all_placeholder_rules_mf2(
            "Source with a {#b}line{#br}{/br}break{/b}",
            "Translation with a {#b}line{#br}{/br}break{/b}",
            Format.android,
        )
        assert result == []

    def test_android_bad_html(self) -> None:
        expected = [
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

        result = _check_all_placeholder_rules_mf2(
            "Source {|<b>| :html}string{|</b>| :html}",
            "Translation with a {|<a>| :html}tag mismatch{|</b>| :html}",
            Format.android,
        )
        assert result == expected
        result = _check_all_placeholder_rules(
            "Source &lt;b&gt;string&lt;/b&gt;",
            "Translation with a &lt;a&gt;tag mismatch&lt;/b&gt;",
            Format.android,
        )
        assert result == expected

    def test_angle_brackets_not_element(self) -> None:
        result = _check_all_placeholder_rules(
            "Press &lt;Enter&gt; to continue",
            "Premi &lt;Invio&gt; per continuare",
            Format.android,
        )
        assert result == []
        result = _check_all_placeholder_rules_mf2(
            "Press {|<Enter>| :html} to continue",
            "Premi {|<Invio>| :html} per continuare",
            Format.android,
        )
        assert result == []

    def test_bare_element_name_not_element(self) -> None:
        translation = "Digita per andare a capo"
        result = _check_all_placeholder_rules(
            "Type &lt;br&gt; for a break", translation, Format.android
        )
        assert result == []
        result = _check_all_placeholder_rules_mf2(
            "Type {|<br>| :html} for a break", translation, Format.android
        )
        assert result == []

    def test_escaped_custom_element_pair(self) -> None:
        expected = [
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
        translation = "testo"
        result = _check_all_placeholder_rules(
            "&lt;myTag&gt;text&lt;/myTag&gt;", translation, Format.android
        )
        assert result == expected
        result = _check_all_placeholder_rules_mf2(
            "{|<myTag>| :html}text{|</myTag>| :html}", translation, Format.android
        )
        assert result == expected

    def test_escaped_element_with_attributes(self) -> None:
        expected = [
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
        result = _check_all_placeholder_rules(
            '<myTag id="1">text</myTag>', "testo", Format.android
        )
        assert result == expected
        result = _check_all_placeholder_rules(
            '&lt;myTag id="1"&gt;text&lt;/myTag&gt;', "testo", Format.android
        )
        assert result == expected
        result = _check_all_placeholder_rules(
            '{|<myTag id="1">| :html}text{|</myTag>| :html}', "testo", Format.android
        )
        assert result == expected

    def test_stray_angle_brackets_ignored(self) -> None:
        """Unable to use literal `<` and `>` like:
          `5 < 10 and x > y`
          `5 < 10 e x > y`
        It would cause `XMLSyntaxError: StartTag: invalid element name, line 1, column 12`
        """
        result = _check_all_placeholder_rules(
            "5 &lt; 10 and x &gt; y",
            "5 &lt; 10 e x &gt; y",
            Format.android,
        )
        assert result == []

    def test_equal_links(self) -> None:
        """Using mf2 parser. Trying with android parser produced an error:
        `Unsupported markup with variable option: Markup('open','a',options={'href': VariableRef('url')})`
        """
        result = _check_all_placeholder_rules_mf2(
            "{#a href=$url}link{/a}", "{#a href=$url}link{/a}"
        )
        assert result == []

    def test_mf2_function_markup(self) -> None:
        """Check Expression without string or VariableRef arg, e.g. function call with no args.
        Using mf2 parser. Trying with android parser produced an error:
        `Unsupported expression: Expression(None,function='current_date')`
        """
        result1 = _check_all_placeholder_rules_mf2(
            "Hello {:current_date}",
            "Hola {:current_date}",
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
        """‰. Trying with xliff parser produced an error:
        `Unsupported expression: Expression('<a href="https://example.com">',function='html')`
        """
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
        result = _check_all_placeholder_rules_mf2(
            f"Read the {{#a href=|{placeholder}|}}policy{{/a}}",
            "Leggi la {#a href=|https://example.com|}policy{/a}",
            format,
        )
        assert result == expected
        result = _check_all_placeholder_rules_mf2(
            f'Read the {{|<a href="{placeholder}">| :html}}policy{{|</a>| :html}}',
            'Leggi la {|<a href="https://example.com">| :html}policy{|</a>| :html}',
            format,
        )
        assert result == expected

    def test_missing_element_suppresses_unnumbered_placeholder_warning(self) -> None:
        """Using mf2 parser. Trying xliff parser produces errors:
        `Unsupported expression: Expression('</a>',function='html')`
        `Improper element nesting for Markup('close','a') in <Element target at 0x107557300>`
        """
        expected = {
            "rule_name": "missing-element",
            "rule_family": "placeholder",
            "message": 'Element <a href="%@"> not found in translation',
            "severity": Severity.WARNING,
        }
        result = _check_all_placeholder_rules_mf2(
            'Read {|<a href="%@">| :html}link{|</a>| :html}',
            "Read link{|</a>| :html}",
            Format.xliff,
        )
        assert result == [expected]

        result = _check_all_placeholder_rules_mf2(
            "Read {#a href=|%@|}link{/a}",
            "Read link{/a}",
            Format.xliff,
        )
        assert result == [expected]

    def test_extra_unnumbered_placeholder_with_markup_attribute(self) -> None:
        result = _check_all_placeholder_rules(
            'Hi %s <a href="%s">link</a>',
            'Hi %s %s <a href="%s">link</a>',
            Format.android,
        )
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
            'Hi <xliff:g xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2" '
            'id="a">Name</xliff:g> and <xliff:g xmlns:xliff="urn:oasis:names:'
            'tc:xliff:document:1.2" id="b">FullName</xliff:g>'
        )
        result = _check_all_placeholder_rules(original, "Salve", Format.android)
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
        original = "Hi %10$s and %2$s"
        result = _check_all_placeholder_rules(original, original, Format.android)
        assert result == []
        original = "Hi {$a :string @source=|%10$s|} and {$b :string @source=|%2$s|}"
        result = _check_all_placeholder_rules_mf2(original, original, Format.android)
        assert result == []

    def test_multi_digit_placeholder_changed(self) -> None:
        """Using mf2 parser for now. The android parser creates broken a `Message`:
        For instance `"Hi %10$s and %2$s"` creates this `Expression`:
          `Expression(VariableRef('arg'),attributes={'source': '%10$'})`
        missing the `s` on the placeholder name.
        https://github.com/mozilla/moz-l10n/issues/237
        """
        original = "Hi {$a :string @source=|%10$s|} and {$b :string @source=|%2$s|}"
        translation = "Ciao {$a :string @source=|%11$s|} e {$b :string @source=|%2$s|}"
        result = _check_all_placeholder_rules_mf2(original, translation, Format.android)
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
            "Source string with a $1",
            "Translation with a $1",
            Format.webext,
        )
        assert result == []

    def test_webext_literal_index_placeholder_as_literal(self) -> None:
        result = _check_all_placeholder_rules(
            "Source string with a $1",
            "Translation with a $$1",
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
        """Testing with mf2. With the webext parser it would complain:
        `Missing placeholders entry for foo`
        """
        result = _check_all_placeholder_rules_mf2(
            "Source string",
            "Translation with a {$arg @source=|$FOO$|}",
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
        """Testing with mf2. With the webext parser it would complain:
        `Missing placeholders entry for foo`
        """
        msg = ".local $FOO = {$arg1 @source=|$1|}\n{{Translation with a {$FOO @source=|$FOO$|}}}"
        result = _check_all_placeholder_rules_mf2(msg, msg, Format.webext)
        assert result == []

    def test_webext_extra_index_placeholder(self) -> None:
        result = _check_all_placeholder_rules_mf2(
            "Source string", "Translation with a $1", Format.webext
        )
        # This should totally not be caught!
        assert result == []

        result = _check_all_placeholder_rules(
            "Source string", "Translation with a $1", Format.webext
        )
        # And THIS should totally be caught!
        assert result == [
            {
                "message": "Placeholder $1 not found in reference",
                "rule_family": "placeholder",
                "rule_name": "extra",
                "severity": Severity.ERROR,
            }
        ]


class TestRest:
    def test_coverage_html_markup_key(self) -> None:
        rule = PLACEHOLDER_CHECKS["extra-element"]
        context = LintContext(Format.android)
        source = PatternMessage([])
        for arg in (VariableRef("div"), "not-a-tag", "<>", "<", ">"):
            target = PatternMessage([Expression(function="html", arg=arg)])
            assert next(iter(rule.check(target, source, context)), None) is None
