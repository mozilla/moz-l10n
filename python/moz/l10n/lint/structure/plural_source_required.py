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

"""plural-source-required -- a pluralized translation needs a pluralized source."""

from __future__ import annotations

from moz.l10n.lint.model import Diagnostic, LintContext, Rule, SourceType, TargetType
from moz.l10n.model import PatternMessage, SelectMessage

NAME = "plural-source-required"
RULE = Rule(
    name=NAME,
    family="structure",
    default_severity="error",
)

MESSAGE = "Plural translation requires plural source"


def check(
    translation: TargetType, source: SourceType, context: LintContext
) -> list[Diagnostic]:
    """
    Report a translation that selects on a plural category
    while its source is a single pattern.

    A source that could not be parsed counts as non-plural, matching the
    conservative behavior of Pontoon's checks.

    gettext : source: SelectMessage trans: PatternMessage(Pattern?) is fine
    fluent + mf2: anything goes
    ini:
    """
    if context.resource_format in ("fluent", "mf2"):
        return []
    if context.resource_format == "gettext" and (
        isinstance(translation, PatternMessage) and isinstance(source, SelectMessage)
    ):
        return []

    if isinstance(translation, SelectMessage) != isinstance(source, SelectMessage):
        return [
            RULE.diagnostic(
                MESSAGE, severity=context.severity_of(RULE), key=context.key
            )
        ]
    return []
