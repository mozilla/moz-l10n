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

from typing import Iterator

from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import Expression, Markup, Message


class ExtraPlaceholder(Rule):
    name = "extra"
    family = "placeholder"
    default_severity = Severity.ERROR

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for placeholder in _get_placeholders(target) - _get_placeholders(source):
            yield self.report(
                context, f"Placeholder {placeholder} not found in reference"
            )


class MissingPlaceholder(Rule):
    name = "missing"
    family = "placeholder"
    default_severity = Severity.WARNING

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for placeholder in _get_placeholders(source) - _get_placeholders(target):
            yield self.report(
                context, f"Placeholder {placeholder} not found in translation"
            )


def _get_placeholders(message: Message) -> set[Expression]:
    return {
        element
        for _, pattern in message
        for element in pattern
        if isinstance(element, Expression)
    }


class ExtraElement(Rule):
    name = "extra-element"
    family = "placeholder"
    default_severity = Severity.ERROR

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for element in _get_elements(target) - _get_elements(source):
            yield self.report(context, f"Element {element} not found in reference")


class MissingElement(Rule):
    name = "missing-element"
    family = "placeholder"
    default_severity = Severity.WARNING

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for element in _get_elements(source) - _get_elements(target):
            yield self.report(context, f"Element {element} not found in translation")


def _get_elements(message: Message) -> set[Markup]:
    return {
        element
        for _, pattern in message
        for element in pattern
        if isinstance(element, Markup)
    }


if __name__ == "__main__":
    import moz.l10n.lint.testing

    moz.l10n.lint.testing.run_from_main()
