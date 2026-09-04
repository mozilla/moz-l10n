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

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import Message, PatternMessage, SelectMessage

MESSAGE = "Plural translation requires plural source"


class PluralSourceRequired(Rule):
    name = "plural-source-required"
    family = "structure"
    default_severity = Severity.ERROR

    def check(
        self, target: Message | None, source: Message | None, context: LintContext
    ) -> Iterator[Diagnostic]:
        """
        Report a translation that selects on a plural category
        while its source is a single pattern.

        A source that could not be parsed counts as non-plural, matching the
        conservative behavior of Pontoon's checks.

        gettext : source: SelectMessage trans: PatternMessage(Pattern) is fine
        fluent + mf2: anything goes
        ini:
        """
        if context.resource_format in (Format.fluent, Format.mf2):
            return

        if context.resource_format is Format.gettext and (
            isinstance(target, PatternMessage) and isinstance(source, SelectMessage)
        ):
            return

        if isinstance(target, SelectMessage) != isinstance(source, SelectMessage):
            yield self.report(MESSAGE, context)

        return
