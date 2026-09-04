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

from collections.abc import Iterator
from typing import Any

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.lint.tools import get_patterns
from moz.l10n.model import Expression, Message

ALLOWED_SEVERITY: Severity = Severity.WARNING
"""Severity used when the resource opts in via `allows_empty_translations`."""
NOT_ALLOWED_MESSAGE = "Empty translations are not allowed"
ALLOWED_MESSAGE = "Empty translation"


class EmptyTranslation(Rule):
    name: str = "empty-translation"
    family: str = "content"
    default_severity: Severity = Severity.ERROR

    def check(
        self, target: Message | None, source: Message | None, context: LintContext
    ) -> Iterator[Diagnostic]:
        """
        Report a wholly empty translation string.

        Resources that opt in keep the empty translation but still get told about
        it, so this downgrades to a warning rather than disappearing.
        This downgrades also applies when the source is empty!
        """
        if context.resource_format not in self.format_severities:
            self._severity = (
                ALLOWED_SEVERITY if source is None or source.is_empty() else None
            )

        if target is None or target.is_empty():
            yield self.report(context=context)
            return

        if context.resource_format is Format.gettext:
            yield from self._check_any_variant(target, context)
            return

        if _has_empty_expressions(target):
            yield self.report(context=context)

    def report(
        self, message: str = "", context: LintContext | None = None, **kwargs: Any
    ) -> Diagnostic:
        severity = (
            context.severity_of(self, self._severity)
            if context is not None
            else self.default_severity
        )
        message = NOT_ALLOWED_MESSAGE if severity is Severity.ERROR else ALLOWED_MESSAGE
        return super().report(message, context, severity=severity)

    def _check_any_variant(
        self, target: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        """
        Report a parsed translation with at least one empty pattern.

        Stricter than `check_message`: for gettext every plural form ends up in
        the same file and an empty one reads as untranslated, so a single blank
        variant is enough to flag.
        """
        if not any(all(el == "" for el in pattern) for pattern in get_patterns(target)):
            return
        yield self.report(context=context)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._severity = None
        self.format_severities: dict[Format, Severity] = {
            Format.fluent: Severity.WARNING,
            Format.gettext: Severity.ERROR,
        }


def _has_empty_expressions(msg: Message) -> bool:
    """Return `True` if ALL elements in a pattern are empty.
    Empty expressions elements are considered empty as well.
    `PatternMessages` have only one pattern and `SelectMessages` may have multiple.
    """
    for pattern in get_patterns(msg):
        for elem in pattern:
            if isinstance(elem, str) and elem != "":
                continue
            if not isinstance(elem, Expression):
                continue
            # in case elem.arg is str or VariableRef:
            if getattr(elem.arg, "name", elem.arg):
                continue
            if not any(elem.variable_refs()):
                return True
    return False
