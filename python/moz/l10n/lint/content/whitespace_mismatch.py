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

import re
from collections.abc import Iterator, Sequence
from os.path import commonprefix
from typing import Any, ClassVar

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import CatchallKey, Message, Pattern


class LeadingWhitespaceMismatch(Rule):
    name: str = "leading-whitespace-mismatch"
    family: str = "content"
    default_severity: Severity = Severity.WARNING

    message: ClassVar[str] = "Leading whitespace mismatch"
    whitespace_regex: ClassVar[re.Pattern[str]] = re.compile(r"^\s+")

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        yield from _check(self, target, source, context)

    @staticmethod
    def iter_direction(sequence: Sequence[Any]) -> Iterator[Any]:
        """Iterate forward through given `sequence`."""
        yield from sequence

    @staticmethod
    def common_whitespace(ws_list: list[str]) -> str:
        return commonprefix(ws_list)


class TrailingWhitespaceMismatch(Rule):
    name: str = "trailing-whitespace-mismatch"
    family: str = "content"
    default_severity: Severity = Severity.WARNING
    format_severities: ClassVar[dict[Format, Severity]] = {
        Format.gettext: Severity.ERROR
    }

    message: ClassVar[str] = "Trailing whitespace mismatch"
    whitespace_regex: ClassVar[re.Pattern[str]] = re.compile(r"\s+$")

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        yield from _check(self, target, source, context)

    @staticmethod
    def iter_direction(sequence: Sequence[Any]) -> Iterator[Any]:
        """Iterate backwards through given `sequence`."""
        yield from reversed(sequence)

    @staticmethod
    def common_whitespace(ws_list: list[str]) -> str:
        return commonprefix([s[::-1] for s in ws_list])[::-1]


_WhitespaceRule = LeadingWhitespaceMismatch | TrailingWhitespaceMismatch


def _check(
    rule: _WhitespaceRule, target: Message, source: Message, context: LintContext
) -> Iterator[Diagnostic]:
    src_whitespace = _get_source_whitespace(rule, source)
    for keys, trg_pattern in target:
        trg_whitespace = _get_whitespace(rule, trg_pattern)
        if trg_whitespace == src_whitespace:
            continue
        yield rule.report(
            context, _make_msg(rule, trg_whitespace, src_whitespace, keys)
        )


def _make_msg(
    rule: _WhitespaceRule,
    trg_whitespace: str,
    src_whitespace: str,
    keys: tuple[str | CatchallKey, ...],
) -> str:
    """Make a whitespace violation report saying under what variant it happened."""
    prefix = (
        f"Variant [{', '.join((k.value or '*') if isinstance(k, CatchallKey) else k for k in keys)}]: "
        if keys
        else ""
    )
    return (
        f"{prefix}{rule.message} (expected {src_whitespace!r}, got {trg_whitespace!r})"
    )


def _get_whitespace(rule: _WhitespaceRule, pattern: Pattern) -> str:
    """Get whitespace from given `pattern` according to the rules `iter_direction`

    Whitespace ONLY patterns return `""` by design to avoid unsolvable mismatches.
    If we'd pass `"   \\n"` a translator would need to make the counterpart
    for instance `"   \\nLOL   \\n"` to satisfy both leading and trailing rules.
    """
    string_stack: list[str] = []
    for element in rule.iter_direction(pattern):
        if not isinstance(element, str):
            break
        string_stack.append(element)
        if element.strip():
            break
    else:
        return ""
    text = "".join(rule.iter_direction(string_stack))
    return match[0] if (match := rule.whitespace_regex.search(text)) else ""


def _get_source_whitespace(rule: _WhitespaceRule, source: Message) -> str:
    """Get common source whitespace as **single** baseline value from all variants.

    Differences in leading or trailing source-whitespace are not our concern here.
    This will be handled by a different validation rule eventually.
    """
    return rule.common_whitespace([_get_whitespace(rule, p) for _, p in source])
