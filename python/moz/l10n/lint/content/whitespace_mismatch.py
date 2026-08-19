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
from typing import Iterator

from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import Format, Message

_MESSAGE = " whitespace mismatch"
_RE_LEADING_WHITESPACE = re.compile(r"^\s+")
_RE_TRAILING_WHITESPACE = re.compile(r"\s+$")


class LeadingWhitespaceMismatch(Rule):
    name: str = "leading-whitespace-mismatch"
    family: str = "content"
    default_severity: Severity = Severity.WARNING
    message = f"Leading {_MESSAGE}"

    def check(
        self, target: Message | None, source: Message | None, context: LintContext
    ) -> Iterator[Diagnostic]:
        if source is None or target is None:
            return

        source_left = self._get_leading_whitespaces(source)
        target_left = self._get_leading_whitespaces(target)
        if source_left == target_left:
            return

        yield self.diagnostic(
            self.message,
            severity=context.severity_of(self),
            message_id=context.id,
            line=1,
            column=1,
        )

    @staticmethod
    def _get_leading_whitespaces(msg: Message) -> str:
        left_match = _RE_LEADING_WHITESPACE.search(msg)
        return left_match.group(0) if left_match else ""


class TrailingWhitespaceMismatch(Rule):
    name: str = "trailing-whitespace-mismatch"
    family: str = "content"
    default_severity: Severity = Severity.WARNING
    message = f"Trailing {_MESSAGE}"

    def __init__(self):
        self.format_severities: dict[Format, Severity] = {
            Format.gettext: Severity.ERROR
        }

    def check(
        self, target: Message | None, source: Message | None, context: LintContext
    ) -> Iterator[Diagnostic]:
        if source is None or target is None:
            return

        source_left = self._get_trailing_whitespaces(source)
        target_left = self._get_trailing_whitespaces(target)
        if source_left == target_left:
            return

        yield self.diagnostic(
            self.message,
            severity=context.severity_of(self),
            message_id=context.id,
            line=1,
            column=1,
        )

    @staticmethod
    def _get_trailing_whitespaces(msg: Message) -> str:
        left_match = _RE_TRAILING_WHITESPACE.search(msg)
        return left_match.group(0) if left_match else ""


# def _get_first_str(s: str | SourceType, raw: str | None) -> str:
#     """TODO: This can probably go as soon as Pontoon no longer deals us fluent."""
#     check_string = (
#         (s.pattern[0] if s.pattern else "") if isinstance(s, PatternMessage) else s
#     )
#     if not isinstance(check_string, str):
#         if raw is None:
#             raise NotImplementedError(
#                 f'TODO: Implement this for format "{type(check_string)}"'
#             )
#         return raw
#     return check_string
