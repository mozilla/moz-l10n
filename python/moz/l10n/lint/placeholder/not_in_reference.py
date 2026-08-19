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

"""placeholder.not-in-reference -- the translation invents a placeholder."""

from __future__ import annotations

from typing import cast

from moz.l10n.lint.model import Diagnostic, LintContext, Rule, SourceType, TargetType
from moz.l10n.lint.placeholder._common import kind_of, match_placeholders
from moz.l10n.model import Message

NAME = "not-in-reference"
RULE = Rule(name=NAME, family="placeholder", default_severity="error")
MESSAGE = "{} {} not found in reference"


def check(
    translation: TargetType, source: SourceType, context: LintContext
) -> list[Diagnostic]:
    """
    Report every placeholder the translation uses that its source does not.

    These are usually typos in a hand-copied specifier. They are errors
    because the runtime has no argument to substitute, so the string either
    renders wrong or crashes the formatter.
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
        for placeholder in match.extra
    ]
