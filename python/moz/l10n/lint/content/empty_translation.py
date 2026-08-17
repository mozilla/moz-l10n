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

"""empty-translation - translation has no visible content."""

from __future__ import annotations

from collections.abc import Iterator

from fluent.syntax import ast as ftl
from moz.l10n.lint.model import (
    Diagnostic,
    LintContext,
    Rule,
    Severity,
    SourceType,
    TargetType,
)
from moz.l10n.model import Message

from .._preview import get_patterns

NAME = "empty-translation"
RULE = Rule(name=NAME, family="content", default_severity="error")

ALLOWED_SEVERITY: Severity = "warning"
"""Severity used when the resource opts in via `allows_empty_translations`."""

NOT_ALLOWED_MESSAGE = "Empty translations are not allowed"
ALLOWED_MESSAGE = "Empty translation"


def check(
    translation: TargetType, source: SourceType, context: LintContext
) -> list[Diagnostic]:
    """
    Report a wholly empty translation string.

    Resources that opt in keep the empty translation but still get told about
    it, so this downgrades to a warning rather than disappearing.
    """
    if isinstance(translation, Message):
        return check_message(translation, context)
    if isinstance(translation, ftl.Message | ftl.Term | ftl.Junk):
        return check_fluent_entry(translation, context)
    return [_report(context)]


def check_message(translation: Message, context: LintContext) -> list[Diagnostic]:
    """
    Report a parsed translation whose patterns are all empty.

    Only literal text counts as content here; a pattern consisting solely of
    placeholders is still considered to say something.
    """
    if context.format_name == "gettext":
        return check_any_variant(translation, context)
    if not translation.is_empty():
        return []
    return [_report(context)]


def check_any_variant(translation: Message, context: LintContext) -> list[Diagnostic]:
    """
    Report a parsed translation with at least one empty pattern.

    Stricter than `check_message`: for gettext every plural form ends up in
    the same file and an empty one reads as untranslated, so a single blank
    variant is enough to flag.
    """
    patterns = get_patterns(translation)
    if not any(all(el == "" for el in pattern) for pattern in patterns):
        return []
    return [_report(context)]


def check_fluent_entry(
    entry: ftl.Message | ftl.Term | ftl.Junk, context: LintContext
) -> list[Diagnostic]:
    """
    Report a Fluent entry with an empty value, attribute, or select variant.

    Fluent spells a deliberately blank pattern as `{ "" }`, which is valid
    syntax but leaves the UI with nothing to show, so it is always reported
    at the opted-in severity rather than blocking the submission.
    """
    if isinstance(entry, ftl.Junk) or not any(_ftl_is_empty(pattern) for pattern in _ftl_leaf_patterns(entry)):
        return []
    diagnostic = RULE.diagnostic(
        ALLOWED_MESSAGE, severity=ALLOWED_SEVERITY, key=context.key or entry.id.name
    )
    return [diagnostic]


def _report(context: LintContext) -> Diagnostic:
    if context.allows_empty_translations:
        return RULE.diagnostic(
            ALLOWED_MESSAGE, severity=ALLOWED_SEVERITY, key=context.key
        )
    return RULE.diagnostic(
        NOT_ALLOWED_MESSAGE, severity=context.severity_of(RULE), key=context.key
    )


def _ftl_leaf_patterns(entry: ftl.Message | ftl.Term) -> Iterator[ftl.Pattern]:
    """
    Every pattern of `entry` that can be rendered on its own.

    A pattern holding a selector contributes its variants instead of itself,
    since only one of them is ever shown.
    """
    values = [entry.value, *(attribute.value for attribute in entry.attributes)]
    for value in values:
        if value is not None:
            yield from _ftl_leaves(value)


def _ftl_leaves(pattern: ftl.Pattern) -> Iterator[ftl.Pattern]:
    selects = [
        element.expression
        for element in pattern.elements
        if isinstance(element, ftl.Placeable)
        and isinstance(element.expression, ftl.SelectExpression)
    ]
    if not selects:
        yield pattern
        return
    for select in selects:
        for variant in select.variants:
            yield from _ftl_leaves(variant.value)


def _ftl_is_empty(pattern: ftl.Pattern) -> bool:
    return all(_ftl_element_is_empty(element) for element in pattern.elements)


def _ftl_element_is_empty(element: ftl.PatternElement) -> bool:
    if isinstance(element, ftl.TextElement):
        return not element.value
    if isinstance(element, ftl.Placeable) and isinstance(
        element.expression, ftl.Literal
    ):
        # `{ "" }` is empty, `{ 0 }` is not.
        return not element.expression.parse()["value"]
    return False
