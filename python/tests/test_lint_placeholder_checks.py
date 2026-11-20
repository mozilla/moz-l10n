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
from moz.l10n.lint import placeholder
from moz.l10n.lint.model import Diagnostic, LintContext, Severity
from moz.l10n.message import parse_message
from moz.l10n.model import (
    CatchallKey,
    Expression,
    Message,
    PatternMessage,
    SelectMessage,
    VariableRef,
)

PLACEHOLDER_CHECKS = {
    "extra": placeholder.ExtraPlaceholder(),
    "missing": placeholder.MissingPlaceholder(),
    "extra-element": placeholder.ExtraElement(),
    "missing-element": placeholder.MissingElement(),
}


def _check_all_placeholder_rules(
    format: Format,
    source_raw: str,
    target_raw: str,
    *,
    is_printf: bool = False,
) -> list[dict[str, Any]]:
    """Parse incoming strings with their dedicated format parser,
    run rules with given format context, and gather diagnostics from all checks.
    """
    if format in (Format.android, Format.xliff):
        pytest.importorskip("lxml")
    xliff_is_xcode = format is Format.xliff and is_printf
    target = parse_message(format, target_raw, xliff_is_xcode=xliff_is_xcode)
    source = parse_message(format, source_raw, xliff_is_xcode=xliff_is_xcode)
    return _call_checks(format, source, target, is_printf)


def _call_checks(
    format: Format, source: Message, target: Message, is_printf: bool = False
) -> list[dict[str, Any]]:
    if format in (Format.android, Format.xliff):
        pytest.importorskip("lxml")
    context = LintContext(format, is_printf=is_printf)
    diagnostics: list[Diagnostic] = []
    for rule in PLACEHOLDER_CHECKS.values():
        diagnostics.extend(rule.check(target, source, context))
    return [dataclasses.asdict(d) for d in diagnostics]


class TestBasic:
    """Basic Presence Checks (Same, Missing, Extra, Mistyped)"""

    def test_android_same_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            Format.android,
            "Source string with a %1$s",
            "Translation with a %1$s",
        )
        assert result == []

    def test_android_missing_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            Format.android,
            "Source string with a %1$s",
            "Translation",
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
            Format.android,
            "Source string with a %1$s",
            "Translation %1",
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
            Format.android,
            "Source string",
            "Translation with a %1$s",
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
            Format.android,
            "New! %s email masks are now available on mobile.",
            "Нав! Акнун ниқобҳои почтаи электронии «%@» дар дастгоҳҳои мобилӣ дастрасанд.",
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
            Format.android,
            "Translation %%",
            "Source percent",
        )
        assert result == []

    def test_android_percent_signs_more(self) -> None:
        result = _check_all_placeholder_rules(
            Format.android, "Source string 100%", "Translation 100%! string 100%"
        )
        assert result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": "Placeholder %! not found in reference",
                "severity": Severity.ERROR,
            }
        ]


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
            format,
            f"Hello {placeholder} and {placeholder}",
            "Hello " + " and ".join([placeholder, placeholder][:count]),
            is_printf=True,
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
            Format.xliff,
            "Hello %@ and %@",
            "Hello %@, %@ and %@",
            is_printf=True,
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
        result = _check_all_placeholder_rules(
            format,
            f"Hello {placeholder} and {placeholder}",
            f"Hello {placeholder}",
            is_printf=True,
        )
        assert result == []

    @pytest.mark.parametrize("source_count, target_count", [(2, 1), (1, 2), (2, 2)])
    def test_repeated_element_with_unnumbered_placeholder(
        self, source_count: int, target_count: int
    ) -> None:
        element = '<a href="%@">link</a>'
        source = " ".join([element] * source_count)
        target = " ".join([element] * target_count)
        result = _check_all_placeholder_rules(
            Format.xliff, source, target, is_printf=True
        )
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

    def test_repeated_unnumbered_placeholder_plural_variants_missing(self) -> None:
        """`android_parse_message` does not support `SelectMessage`.
        That's why we construct one and pass it into `_call_checks`
        and not have strings passed into `_check_all_placeholder_rules`.
        """
        pytest.importorskip("lxml")
        ph = "%s"
        android_msg1 = parse_message(Format.android, f"For {ph} and {ph}")
        assert isinstance(android_msg1, PatternMessage)
        original = SelectMessage(
            declarations={"n": Expression(VariableRef("n"), function="number")},
            selectors=(VariableRef("n"),),
            variants={
                ("one",): android_msg1.pattern,
                (CatchallKey(None),): android_msg1.pattern,
            },
        )
        android_msg2 = parse_message(Format.android, f"For {ph}")
        assert isinstance(android_msg2, PatternMessage)
        translation = dataclasses.replace(
            original,
            variants={
                ("one",): android_msg2.pattern,
                ("few",): android_msg2.pattern,
                (CatchallKey(None),): android_msg2.pattern,
            },
        )
        assert _call_checks(Format.android, original, translation, is_printf=True) == [
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder %s has fewer occurrences in translation (expected 2, found 1)",
                "severity": Severity.WARNING,
            }
        ]

    def test_repeated_unnumbered_placeholder_plural_variants(self) -> None:
        """`android_parse_message` does not support `SelectMessage`.
        That's why we construct one and pass it into `_call_checks`
        and not have strings passed into `_check_all_placeholder_rules`.
        """
        pytest.importorskip("lxml")
        ph = "%s"
        android_msg = parse_message(Format.android, f"For {ph} and {ph}")
        assert isinstance(android_msg, PatternMessage)
        original = SelectMessage(
            declarations={"n": Expression(VariableRef("n"), function="number")},
            selectors=(VariableRef("n"),),
            variants={
                ("one",): android_msg.pattern,
                (CatchallKey(None),): android_msg.pattern,
            },
        )
        translation = dataclasses.replace(
            original,
            variants={
                ("one",): android_msg.pattern,
                ("few",): android_msg.pattern,
                (CatchallKey(None),): android_msg.pattern,
            },
        )
        assert _call_checks(Format.android, original, translation, is_printf=True) == []

    def test_repeated_unnumbered_placeholder_fewer_source_variants(self) -> None:
        """Translations can have fewer plural forms than the source.

        `android_parse_message` does not support `SelectMessage`.
        That's why we construct one and pass it into `_call_checks`
        and not have strings passed into `_check_all_placeholder_rules`.
        """
        pytest.importorskip("lxml")
        variant1 = parse_message(Format.android, "one %s of %s")
        variant2 = parse_message(Format.android, "%s items")
        variant3 = parse_message(Format.android, "%s items")
        assert isinstance(variant1, PatternMessage)
        assert isinstance(variant2, PatternMessage)
        assert isinstance(variant3, PatternMessage)

        original_msg = SelectMessage(
            declarations={"n": Expression(VariableRef("n"), function="number")},
            selectors=(VariableRef("n"),),
            variants={
                ("one",): variant1.pattern,
                (CatchallKey(None),): variant2.pattern,
            },
        )

        translation_msg = SelectMessage(
            declarations={"n": Expression(VariableRef("n"), function="number")},
            selectors=(VariableRef("n"),),
            variants={(CatchallKey(None),): variant3.pattern},
        )
        assert (
            _call_checks(Format.android, original_msg, translation_msg, is_printf=True)
            == []
        )

    @pytest.mark.parametrize("count", [1, 3])
    def test_unnumbered_placeholder_mismatch_in_one_plural_variant(
        self, count: int
    ) -> None:
        """`xliff_parse_message` does not support `SelectMessage`.
        That's why we construct one and pass it into `_call_checks`
        and not have strings passed into `_check_all_placeholder_rules`.
        """
        pytest.importorskip("lxml")
        direction = "fewer" if count == 1 else "more"
        rule_name = "missing" if count == 1 else "extra"
        severity = Severity.WARNING if count == 1 else Severity.ERROR

        xliff_msgX = parse_message(
            Format.xliff, f" {'%@ ' * count}", xliff_is_xcode=True
        )
        xliff_msg2 = parse_message(Format.xliff, " %@ %@ ", xliff_is_xcode=True)
        assert isinstance(xliff_msgX, PatternMessage)
        assert isinstance(xliff_msg2, PatternMessage)

        original = SelectMessage(
            declarations={"n": Expression(VariableRef("n"), function="number")},
            selectors=(VariableRef("n"),),
            variants={
                ("one",): xliff_msg2.pattern,
                (CatchallKey(None),): xliff_msg2.pattern,
            },
        )
        translation = SelectMessage(
            declarations={"n": Expression(VariableRef("n"), function="number")},
            selectors=(VariableRef("n"),),
            variants={
                ("one",): xliff_msgX.pattern,
                (CatchallKey(None),): xliff_msg2.pattern,
            },
        )
        assert _call_checks(Format.xliff, original, translation, is_printf=True) == [
            {
                "rule_name": rule_name,
                "rule_family": "placeholder",
                "message": f"Placeholder %@ has {direction} occurrences in translation (expected 2, found {count})",
                "severity": severity,
            }
        ]

    @pytest.mark.xfail(
        strict=True,
        reason="#246 - Escaped xml not yet parsed into Markup(..'escaped': True)",
    )
    def test_missing_elements_in_different_source_variants(self) -> None:
        pytest.importorskip("lxml")
        variant1 = parse_message(Format.xliff, '<a href="%@">link</a>')
        variant2 = parse_message(Format.xliff, '<a title="%@">link</a>')
        variant3 = parse_message(Format.xliff, "link&lt;/a&gt;")
        assert isinstance(variant1, PatternMessage)
        assert isinstance(variant2, PatternMessage)
        assert isinstance(variant3, PatternMessage)

        original = SelectMessage(
            declarations={"n": Expression(VariableRef("n"), function="number")},
            selectors=(VariableRef("n"),),
            variants={
                ("one",): variant1.pattern,
                (CatchallKey(None),): variant2.pattern,
            },
        )

        translation = SelectMessage(
            declarations={"n": Expression(VariableRef("n"), function="number")},
            selectors=(VariableRef("n"),),
            variants={(CatchallKey(None),): variant3.pattern},
        )

        result = _call_checks(Format.xliff, original, translation, is_printf=True)
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

    def test_android_good_html_as_markup(self) -> None:
        """Test escaped markup `<b>line<br>break</b>`

        Note: This succeeds but actually produces markup nodes as
        `Expression('<b>',function='html')` that we no longer check for.
        We could mock the expected structure and fail here
        but #246 is not even started and all that should be done there.
        """
        result = _check_all_placeholder_rules(
            Format.android,
            "Source with a &lt;b&gt;line&lt;br&gt;break&lt;/b&gt;",
            "Translation with a &lt;b&gt;line&lt;br&gt;break&lt;/b&gt;",
        )
        assert result == []

    def test_android_standalone_markup(self) -> None:
        """Test `<standalone/>` markup."""
        result = _check_all_placeholder_rules(
            Format.android,
            "Source with a &lt;b&gt;line&lt;br/&gt;break&lt;/b&gt;",
            "Translation with &lt;b&gt;no&lt;/b&gt; line break",
        )
        assert result == [
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder &lt;br/&gt; not found in translation",
                "severity": Severity.WARNING,
            }
        ]

    @pytest.mark.xfail(
        strict=True,
        reason="#246 - Escaped xml not yet parsed into Markup(..'escaped': True)",
    )
    def test_android_bad_html(self) -> None:
        result = _check_all_placeholder_rules(
            Format.android,
            "Source &lt;b&gt;string&lt;/b&gt;",
            "Translation with a &lt;a&gt;tag mismatch&lt;/b&gt;",
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

    @pytest.mark.xfail(
        strict=True,
        reason="#246 - Escaped xml not yet parsed into Markup(..'escaped': True)",
    )
    def test_angle_brackets_not_element(self) -> None:
        result = _check_all_placeholder_rules(
            Format.android,
            "Press &lt;Enter&gt; to continue",
            "Premi &lt;Invio&gt; per continuare",
        )
        assert result == []

        result = _check_all_placeholder_rules(
            Format.android,
            "Type &lt;br&gt; for a break",
            "Digita per andare a capo",
        )
        assert result == []

    @pytest.mark.xfail(
        strict=True,
        reason="#246 - Escaped xml not yet parsed into Markup(..'escaped': True)",
    )
    def test_escaped_custom_element_pair(self) -> None:
        result = _check_all_placeholder_rules(
            Format.android,
            "&lt;myTag&gt;text&lt;/myTag&gt;",
            "testo",
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

    def test_un_escaped_element_with_attributes(self) -> None:
        result = _check_all_placeholder_rules(
            Format.android, '<myTag id="1">text</myTag>', "testo"
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

    @pytest.mark.xfail(
        strict=True,
        reason="#246 - Escaped xml not yet parsed into Markup(..'escaped': True)",
    )
    def test_stray_angle_brackets_ignored(self) -> None:
        result = _check_all_placeholder_rules(
            Format.android,
            "5 &lt; 10 and x &gt; y",
            "5 &lt; 10 e x &gt; y",
        )
        assert result == []

    @pytest.mark.xfail(strict=True, reason="#250 - `% o` is turned into an Expression")
    def test_percentage_whitespace(self) -> None:
        result = _check_all_placeholder_rules(
            Format.android,
            "Now 25% off!!!",
            "Jetzt 25 Prozent billiger!!",
        )
        assert result == []

    def test_element_attribute_order(self) -> None:
        result = _check_all_placeholder_rules(
            Format.xliff,
            'Read the <a href="https://example.com" title="Policy">policy</a>',
            'Leggi la <a title="Policy" href="https://example.com">policy</a>',
            is_printf=True,
        )
        assert result == []


class TestAttributes:
    """Placeholders in Attributes & Suppression Cascades"""

    @pytest.mark.parametrize(
        "format, placeholder",
        [(Format.xliff, "%1$@"), (Format.android, "%1$s")],
    )
    def test_changed_placeholder_in_element(
        self, format: Format, placeholder: str
    ) -> None:
        result = _check_all_placeholder_rules(
            format,
            f'Read the <a href="{placeholder}">policy</a>',
            'Leggi la <a href="https://example.com">policy</a>',
        )
        assert result == [
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

    @pytest.mark.parametrize(
        ("format", "placeholder"), [(Format.android, "%s"), (Format.xliff, "%@")]
    )
    def test_missing_element_suppresses_unnumbered_placeholder_warning(
        self, format: Format, placeholder: str
    ) -> None:
        expected = [
            {
                "rule_name": "missing-element",
                "rule_family": "placeholder",
                "message": "Element </a> not found in translation",
                "severity": Severity.WARNING,
            },
            {
                "rule_name": "missing-element",
                "rule_family": "placeholder",
                "message": f'Element <a href="{placeholder}"> not found in translation',
                "severity": Severity.WARNING,
            },
        ]
        result = _check_all_placeholder_rules(
            format,
            f'Read <a href="{placeholder}">link</a>',
            "Read link",
        )
        assert result == expected

    @pytest.mark.parametrize(
        "format, placeholder",
        [
            (Format.xliff, "%@"),
            (Format.xliff, "%#x"),
            (Format.android, "%s"),
            (Format.android, "%02d"),
        ],
    )
    def test_extra_unnumbered_placeholder_with_markup_attribute(
        self, format: Format, placeholder: str
    ) -> None:
        result = _check_all_placeholder_rules(
            format,
            f'Hi {placeholder} <a href="{placeholder}">link</a>',
            f'Hi {placeholder} {placeholder} <a href="{placeholder}">link</a>',
            is_printf=True,
        )
        assert result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": f"Placeholder {placeholder} has more occurrences in translation (expected 2, found 3)",
                "severity": Severity.ERROR,
            }
        ]


class TestProtections:
    """Protections & Multi-digit Placeholders"""

    @pytest.mark.xfail(
        strict=True,
        reason="#244 - Currently fails because it's missing the namespace declaration.",
    )
    def test_protections_with_shared_substring(self) -> None:
        """TODO For when #244 lands: We replaced our tokenizer with `serialize_message`!
        This means we need to amend the expected report messages. It won't be this behemoth
        `<xliff:g xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2" id="a">Name</xliff:g>`
        but probably `<xliff:g id="a">Name</xliff:g>` instead of `Name` for instance?
        """
        original = (
            'Hi <xliff:g id="a">Name</xliff:g> and <xliff:g id="b">FullName</xliff:g>'
        )
        result = _check_all_placeholder_rules(Format.android, original, "Salve")
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

    def test_multi_digit_placeholder_changed(self) -> None:
        result = _check_all_placeholder_rules(
            Format.android, "Hi %10$s and %2$s", "Ciao %11$s e %2$s"
        )
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
            Format.webext,
            "Source string with a $1",
            "Translation with a $1",
        )
        assert result == []

    def test_webext_literal_index_placeholder_as_literal(self) -> None:
        result = _check_all_placeholder_rules(
            Format.webext,
            "Source string with a $1",
            "Translation with a $$1",
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
        source = parse_message(Format.webext, "Source string")
        target = parse_message(
            Format.webext,
            "Translation with a $FOO$",
            webext_placeholders={"foo": {"content": "BAR"}},
        )
        result = _call_checks(Format.webext, source, target)
        assert result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": "Placeholder $FOO$ not found in reference",
                "severity": Severity.ERROR,
            }
        ]

    def test_webext_literal_named_placeholder_as_placeholder(self) -> None:
        placeholders = {"foo": {"content": "$1"}}
        source = parse_message(
            Format.webext, "Source with a $FOO$", webext_placeholders=placeholders
        )
        target = parse_message(
            Format.webext,
            "Translation with a $FOO$",
            webext_placeholders=placeholders,
        )
        result = _call_checks(Format.webext, source, target)
        assert result == []

    def test_webext_extra_index_placeholder(self) -> None:
        result = _check_all_placeholder_rules(
            Format.webext, "Source string", "Translation with a $1"
        )
        # And THIS should totally be caught.
        assert result == [
            {
                "message": "Placeholder $1 not found in reference",
                "rule_family": "placeholder",
                "rule_name": "extra",
                "severity": Severity.ERROR,
            }
        ]


class TestRest:
    def test_plain_variable_placeholder(self) -> None:
        """Test coverage for Expression nodes with a VariableRef argument (e.g. {$user})."""
        result = _check_all_placeholder_rules(
            Format.fluent,
            "Source { $user }",
            "Hello { $user }",
        )
        assert result == []

        missing_result = _check_all_placeholder_rules(
            Format.fluent, "Source { $user }", "Hello"
        )
        assert missing_result == [
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder { $user } not found in translation",
                "severity": Severity.WARNING,
            }
        ]

    def test_entity_placeholder(self) -> None:
        """Test coverage for `Expression` nodes with :entity function."""
        result = _check_all_placeholder_rules(
            Format.android,
            "Welcome to &brand;",
            "Source &brand;",
        )
        assert result == []

        missing_result = _check_all_placeholder_rules(
            Format.android,
            "Welcome to &brand;!",
            "Wilkommen bei &marke;!",
        )
        assert missing_result == [
            {
                "rule_name": "extra",
                "rule_family": "placeholder",
                "message": "Placeholder &marke; not found in reference",
                "severity": Severity.ERROR,
            },
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder &brand; not found in translation",
                "severity": Severity.WARNING,
            },
        ]

    def test_literal_expression_placeholder(self) -> None:
        """Check Expression nodes with literal arguments (`{42}`)."""
        result = _check_all_placeholder_rules(
            Format.fluent, "Source: {42}", "Count: {42}"
        )
        assert result == []

        missing_result = _check_all_placeholder_rules(
            Format.fluent, "Source: {42}", "Count"
        )
        assert missing_result == [
            {
                "rule_name": "missing",
                "rule_family": "placeholder",
                "message": "Placeholder { 42 } not found in translation",
                "severity": Severity.WARNING,
            }
        ]
