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

"""message-id-mismatch -- the translation's id must match the source's id."""

from __future__ import annotations

from fluent.syntax import ast as ftl
from moz.l10n.lint.model import (
    Diagnostic,
    LintContext,
    Rule,
    SourceType,
    TargetType,
    get_line_col,
)

NAME = "message-id-mismatch"
RULE = Rule(name=NAME, family="structure", default_severity="error")

MESSAGE = "Translation key needs to match source string key"


def check(
    translation: TargetType, source: SourceType, context: LintContext
) -> list[Diagnostic]:
    """
    Report a Fluent translation whose entry id differs from the source's.

    Renaming the entry would silently orphan the translation, so the id is
    treated as part of the message identity rather than as content.
    """
    if not isinstance(source, (ftl.Message, ftl.Term)) or not isinstance(
        translation, (ftl.Message, ftl.Term)
    ):
        return []

    if source.id.name == translation.id.name:
        return []

    offset = translation.id.span.start if translation.id.span else 0
    line, column = get_line_col(context.raw_translation, offset)
    return [
        RULE.diagnostic(
            MESSAGE,
            severity=context.severity_of(RULE),
            key=context.key or translation.id.name,
            line=line,
            column=column,
        )
    ]
