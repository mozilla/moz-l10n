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

from fluent.syntax import FluentParser, ast
from moz.l10n.formats.fluent import fluent_parse
from moz.l10n.formats.mf2 import mf2_parse_message
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.lint.tools import get_line_column
from moz.l10n.model import Format, Message

ftl_parser = FluentParser()

ERROR_PATTERN = "{} parse error: {}"


class SourceMessageError(Rule):
    name = "source-error"
    family = "parse"
    default_severity = Severity.WARNING

    def parse_check(
        self, raw_source: str | None, context: LintContext
    ) -> tuple[Message | None, Diagnostic | None]:
        """
        Try parsing the raw source message according to context.
        Returned parsed Message if succeeded. Otherwise None.
        Unparsable source is not a translators business.
        """
        if not raw_source:
            return None, None
        parse_type = "Source message"
        parser = (
            parse_message_mf2
            if context.resource_format != Format.fluent
            else parse_message_ftl
        )
        source, diagnostic = parser(raw_source, context, self, parse_type)
        return source, diagnostic


class TargetMessageError(Rule):
    name = "target-error"
    family = "parse"
    default_severity = Severity.ERROR

    def parse_check(
        self, raw_target: str | None, context: LintContext
    ) -> tuple[Message | None, Diagnostic | None]:
        """
        Try parsing the raw target message according to context.
        Returned parsed Message if succeeded. Otherwise:
        target parse failure is terminal! Pass `None` downstream.
        """
        # Emptiness is content.empty-target's call, not a parse error.
        if not raw_target:
            return None, None

        parse_type = "Target message"
        if context.resource_format == Format.fluent:
            target, diagnostic = parse_message_ftl(
                raw_target, context, self, parse_type
            )
        else:
            target, diagnostic = parse_message_mf2(
                raw_target, context, self, parse_type
            )

        if diagnostic:
            return None, diagnostic

        return target, None


def parse_message_mf2(
    raw: str, context: LintContext, rule: Rule, parse_type: str
) -> tuple[Message | None, Diagnostic | None]:
    """Try parsing a raw string as MF2."""
    try:
        return mf2_parse_message(raw), None
    except ValueError as error:
        line, column = get_line_column(raw, getattr(error, "pos", 0))
        diagnostic = rule.diagnostic(
            ERROR_PATTERN.format(parse_type, error),
            severity=context.severity_of(rule),
            id=context.id,
            line=line,
            column=column,
        )
        return None, diagnostic


def parse_message_ftl(
    raw: str, context: LintContext, rule: Rule, parse_type: str
) -> tuple[Message | None, Diagnostic | None]:
    # msg = ftl_parser.parse_entry(raw)
    try:
        msg = next(fluent_parse(raw).all_entries()).value
    except ValueError as error:
        line, column = get_line_column(raw, getattr(error, "pos", 0))
        diagnostic = rule.diagnostic(
            ERROR_PATTERN.format(parse_type, error),
            severity=context.severity_of(rule),
            id=context.id,
            line=line,
            column=column,
        )
        return None, diagnostic

    if (
        isinstance(msg, ast.Junk)
        and msg.annotations
        and msg.annotations[0].message is not None
    ):
        diagnostic = rule.diagnostic(
            ERROR_PATTERN.format(parse_type, msg.annotations[0].message),
            severity=context.severity_of(rule),
            id=context.id,
        )
        return None, diagnostic

    return msg, None
