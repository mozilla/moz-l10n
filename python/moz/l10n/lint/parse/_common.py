from fluent.syntax import FluentParser, ParseError, ast
from moz.l10n.formats.mf2 import mf2_parse_message
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, get_line_col
from moz.l10n.model import Message

ftl_parser = FluentParser()
ERROR_PATTERN = "{} parse error: {}"


def parse_fluent(
    raw: str, context: LintContext, rule: Rule, parse_type: str = ""
) -> tuple[ast.EntryType | None, Diagnostic | None]:
    """
    Use `FluentParser` to ingest incoming raw strings.
    In case an `ast.Junk` is returned report the first annotation as violation.
    """
    try:
        entry = ftl_parser.parse_entry(raw)
    except ParseError as error:
        return None, rule.diagnostic(
            ERROR_PATTERN.format(parse_type, error),
            severity=context.severity_of(rule),
            key=context.key,
        )

    if (
        isinstance(entry, ast.Junk)
        and entry.annotations
        and entry.annotations[0].message is not None
    ):
        return entry, rule.diagnostic(
            entry.annotations[0].message,
            severity=context.severity_of(rule),
            key=context.key,
        )
    return entry, None


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
            key=context.key,
            line=line,
            column=column,
        )
        return None, diagnostic
