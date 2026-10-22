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
from collections.abc import Iterator
from typing import ClassVar

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import CatchallKey, Message, Pattern


class LeadingWhitespaceMismatch(Rule):
    name: str = "leading-whitespace-mismatch"
    family: str = "content"
    default_severity: Severity = Severity.WARNING

    _message: ClassVar[str] = "Leading whitespace mismatch"
    _whitespace_regex: ClassVar[re.Pattern[str]] = re.compile(r"^\s+")

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        # Get common source whitespace from all variants.
        ws_list = [self._get_leading_whitespace(p) for _, p in source]
        src_whitespace = _commonprefix(ws_list)

        for keys, trg_pattern in target:
            trg_whitespace = self._get_leading_whitespace(trg_pattern)
            if trg_whitespace == src_whitespace:
                continue
            message = _make_msg(self._message, trg_whitespace, src_whitespace, keys)
            yield self.report(context, message)

    def _get_leading_whitespace(self, pattern: Pattern) -> str:
        """Accumulate and return leading whitespace from given pattern.

        Note: Whitespace-ONLY patterns return `""` to avoid reporting duplicate
        mismatches on both leading and trailing rules for the same text span.
        """
        string_stack: str = ""
        for element in pattern:
            if not isinstance(element, str):
                break
            string_stack += element
            if element.strip():
                break
        else:
            return ""
        return match[0] if (match := self._whitespace_regex.match(string_stack)) else ""


class TrailingWhitespaceMismatch(Rule):
    name: str = "trailing-whitespace-mismatch"
    family: str = "content"
    default_severity: Severity = Severity.WARNING
    format_severities: ClassVar[dict[Format, Severity]] = {
        Format.gettext: Severity.ERROR
    }

    _message: ClassVar[str] = "Trailing whitespace mismatch"
    _whitespace_regex: ClassVar[re.Pattern[str]] = re.compile(r"\s+$")

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        # Get common source whitespace from all variants.
        ws_list = [self._get_trailing_whitespace(p) for _, p in source]
        src_whitespace = _commonprefix([s[::-1] for s in ws_list])[::-1]

        for keys, trg_pattern in target:
            trg_whitespace = self._get_trailing_whitespace(trg_pattern)
            if trg_whitespace == src_whitespace:
                continue
            message = _make_msg(self._message, trg_whitespace, src_whitespace, keys)
            yield self.report(context, message)

    def _get_trailing_whitespace(self, pattern: Pattern) -> str:
        """Accumulate and return trailing whitespace from given pattern.

        Note: Whitespace-ONLY patterns return `""` to avoid reporting duplicate
        mismatches on both leading and trailing rules for the same text span.
        """
        string_stack: str = ""
        for element in reversed(pattern):
            if not isinstance(element, str):
                break
            string_stack = element + string_stack
            if element.strip():
                break
        else:
            return ""
        return (
            match[0] if (match := self._whitespace_regex.search(string_stack)) else ""
        )


def _make_msg(
    message: str,
    trg_whitespace: str,
    src_whitespace: str,
    keys: tuple[str | CatchallKey, ...],
) -> str:
    """Make a whitespace violation report saying under what variant it happened."""
    prefix = f"Variant [{', '.join((str(k) or '*') for k in keys)}]: " if keys else ""
    return f"{prefix}{message} (expected {src_whitespace!r}, got {trg_whitespace!r})"


def _commonprefix(sequence: list[str]) -> str:
    """Given a list of strings, return the longest common leading component."""
    if not sequence:
        return ""
    if len(sequence) == 1:
        return sequence[0]
    s1, s2 = min(sequence), max(sequence)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1
