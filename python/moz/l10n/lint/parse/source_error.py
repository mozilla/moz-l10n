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

"""parse.source-error -- the reference resource cannot be parsed."""

from __future__ import annotations

from fluent.syntax import FluentParser, ParseError, ast
from moz.l10n.formats.mf2 import MF2ParseError, mf2_parse_message
from moz.l10n.lint.model import SEVERITY, Diagnostic, LintContext, Rule, SourceType
from moz.l10n.model import Message

NAME = "source-error"
RULE = Rule(name=NAME, family="parse", default_severity=SEVERITY.warning)

ftl_parser = FluentParser()


def parse_check(raw: str, context: LintContext) -> tuple[SourceType, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    if context.format_name() == "fluent":
        entity, fluent_diagnostic = parse_fluent(raw, context)
        if fluent_diagnostic:
            diagnostics.append(fluent_diagnostic)

    else:
        entity, mf2_diagnostic = parse_mf2(raw, context)
        if mf2_diagnostic:
            diagnostics.append(mf2_diagnostic)
    return entity, diagnostics


def parse_fluent(
    source: str, context: LintContext
) -> tuple[ast.EntryType | None, Diagnostic | None]:
    """
    Use `FluentParser` to ingest incoming raw source.
    In case an `ast.Junk` is returned report the first annotation as violation.
    """
    try:
        entry = ftl_parser.parse_entry(source)
    except ParseError as error:
        return None, RULE.diagnostic(
            f"Fluent Source parse error: {error}",
            severity=context.severity_of(RULE),
            key=context.key,
        )

    if (
        isinstance(entry, ast.Junk)
        and entry.annotations
        and entry.annotations[0].message is not None
    ):
        return entry, RULE.diagnostic(
            entry.annotations[0].message,
            severity=context.severity_of(RULE),
            key=context.key,
        )
    return entry, None


def parse_mf2(
    source: str, context: LintContext
) -> tuple[Message | None, Diagnostic | None]:
    """
    Parse the reference `source` as MF2.

    An unparsable source is the source's problem rather than the translator's,
    so this is a warning: the remaining rules carry on without a reference.
    """
    try:
        return mf2_parse_message(source), None
    except MF2ParseError as error:
        line, column = get_line_col(source, getattr(error, "pos", 0))
        diagnostic = RULE.diagnostic(
            f"MF2 Source parse error: {error}",
            severity=context.severity_of(RULE),
            key=context.key,
            line=line,
            column=column,
        )
        return None, diagnostic


def get_line_col(source: str, pos: int) -> tuple[int, int]:
    prefix = source[:pos]
    line = prefix.count("\n") + 1
    column = pos - prefix.rfind("\n")
    return line, column
