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

"""parse.target-error - The target cannot be parsed in its defined format."""

from __future__ import annotations

from moz.l10n.formats.mf2 import mf2_parse_message
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity, get_line_col
from moz.l10n.model import Message

ERROR_PATTERN = "{} parse error: {}"


class SourceError(Rule):
    name = "source-error"
    family = "parse"
    default_severity = Severity.WARNING

    def parse_check(self, raw_source: str, context: LintContext) -> tuple[Message | None, Diagnostic | None]:
        """
        Try parsing the raw source according to context.
        Returned parsed Message if succeeded. Otherwise None.
        Unparsable source is not a translators business.
        """
        target, diagnostic = parse_mf2(raw_source, context, self, "source")
        return target, diagnostic


class TargetError(Rule):
    name = "target-error"
    family = "parse"
    default_severity = Severity.ERROR

    def parse_check(self, raw_target: str, context: LintContext) -> tuple[Message | None, Diagnostic | None]:
        """
        Try parsing the raw target according to context.
        Returned parsed Message if succeeded. Otherwise:
        target parse failure is terminal! Pass `None` downstream.
        """
        # Emptiness is content.empty-target's call, not a parse error.
        if not raw_target:
            return None, None

        target, diagnostic = parse_mf2(raw_target, context, self, "target")
        if diagnostic:
            return None, diagnostic

        return target, None


def parse_mf2(
    raw: str, context: LintContext, rule: Rule, parse_type: str
) -> tuple[Message | None, Diagnostic | None]:
    """Try parsing a raw string as MF2."""
    try:
        return mf2_parse_message(raw), None
    except ValueError as error:
        line, column = get_line_col(raw, getattr(error, "pos", 0))
        diagnostic = rule.diagnostic(
            ERROR_PATTERN.format(parse_type, error),
            severity=context.severity_of(rule),
            message_id=context.id,
            line=line,
            column=column,
        )
        return None, diagnostic
