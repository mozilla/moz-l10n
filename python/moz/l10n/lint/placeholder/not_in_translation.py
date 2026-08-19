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

"""placeholder.not-in-translation - A source placeholder went missing."""

from __future__ import annotations

from typing import cast

from moz.l10n.lint.model import Diagnostic, LintContext, Rule, SourceType, TargetType
from moz.l10n.model import Message

from ._common import kind_of, match_placeholders

NAME = "not-in-translation"
RULE = Rule(name=NAME, family="placeholder", default_severity="warning")
MESSAGE = "{} {} not found in translation"


def check(
    translation: TargetType, source: SourceType, context: LintContext
) -> list[Diagnostic]:
    """
    Report every source placeholder the translation leaves out.

    A warning rather than an error: some languages genuinely do without a
    given argument, so this needs a human to judge it.
    """
    if translation is None or source is None or context.is_fluent:
        return []

    match = match_placeholders(
        cast(Message, translation), cast(Message, source), context.format_name
    )
    return [
        RULE.diagnostic(
            MESSAGE.format(kind_of(placeholder), placeholder),
            severity=context.severity_of(RULE),
            key=context.key,
        )
        for placeholder in match.missing
    ]
