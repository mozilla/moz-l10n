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
from typing import Any, ClassVar

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import Expression, Message

ALLOWED_SEVERITY: Severity = Severity.WARNING
"""Severity used when translations may be empty."""
NOT_ALLOWED_MESSAGE = "Empty translations are not allowed"
ALLOWED_MESSAGE = "Empty translation"


class EmptyTranslation(Rule):
    name: str = "empty-translation"
    family: str = "content"
    default_severity: Severity = Severity.ERROR
    format_severities: ClassVar[dict[Format, Severity]] = {
        Format.fluent: Severity.WARNING,
        Format.gettext: Severity.ERROR,
    }

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        """
        Report a wholly empty translation string.

        If `source` is empty nothing is reported here.
        On `Format.gettext` this trips for any variant being empty.
        If empty translation are allowed report downgrades to warning.
        """
        if source.is_empty():
            return

        if _has_all_empty_pattern(target):
            yield self.report(context)

    def report(
        self, context: LintContext | None = None, message: str = "", **kwargs: Any
    ) -> Diagnostic:
        severity = (
            context.severity_of(self) if context is not None else self.default_severity
        )
        message = NOT_ALLOWED_MESSAGE if severity is Severity.ERROR else ALLOWED_MESSAGE
        return super().report(context, message)


def _has_all_empty_pattern(msg: Message) -> bool:
    """Return `True` if ALL elements in ANY of the patterns are empty.
    "Empty" is str == "" and empty expressions.

    Looping over the elements of a pattern:
    * break the loop as soon as a non-empty was found
    * else: not breaking : all elements were empty in THIS pattern!
    * not returned already : all patterns were not entirely empty.
    """
    for _, pattern in msg:
        if not pattern:
            return True

        for elem in pattern:
            if isinstance(elem, str) and elem != "":
                break
            if not isinstance(elem, Expression):
                continue
            # Skip in case elem.arg is valid str or VariableRef argument:
            if getattr(elem.arg, "name", elem.arg):
                break
            if any(elem.variable_refs()):
                break
        else:
            return True
    return False
