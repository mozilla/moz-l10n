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
from os.path import commonprefix
from typing import Any

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import CatchallKey, Message, Pattern, PatternMessage, SelectMessage

_MESSAGE = " whitespace mismatch"
_RE_LEADING_WHITESPACE = re.compile(r"^\s+")
_RE_TRAILING_WHITESPACE = re.compile(r"\s+$")


class _WhitespaceMismatch(Rule):
    family: str = "content"
    default_severity: Severity = Severity.WARNING

    _message: str = ""
    _whitespace_regex: re.Pattern[str]

    def _iterate(self, object: list[Any]) -> Iterator[Any]:
        raise NotImplementedError()

    def _get_whitespace(self, pattern: Pattern) -> str:
        """Get leading or trailing whitespace.

        Accumulates strings from pattern in according direction
        until it finds a non whitespace string or non-string.

        Whitespace ONLY strings return `""` by design.
        If we'd pass `"   \\n"` a translator would need to make the counterpart
        for instance `"   \\nLOL   \\n"` to satisfy both leading and trailing rules.
        """
        if not pattern:
            return ""

        string_stack: list[str] = []
        # loop pattern forward or backward for leading/trailing
        for element in self._iterate(pattern):
            # stop at Markup or Expression
            if not isinstance(element, str):
                break
            # collect all whitespace
            if not element.strip():
                string_stack.append(element)
                continue
            # append last string that's not only whitespace
            string_stack.append(element)
            break
        else:
            # Loop exhausted: pattern has whitespace only
            return ""

        if match := self._whitespace_regex.search("".join(self._iterate(string_stack))):
            return match[0]
        return ""

    def _get_common_whitespace(self, whitespace_list: list[str]) -> str:
        """Calculate the longest common whitespace sequence across variants."""
        raise NotImplementedError()

    def _get_source_whitespace(self, source: Message) -> str:
        """Determine expected source whitespace as single baseline value."""
        if isinstance(source, PatternMessage):
            return self._get_whitespace(source.pattern)

        if isinstance(source, SelectMessage):
            ws_list = [self._get_whitespace(p) for p in source.variants.values()]
            if not ws_list:
                return ""
            return self._get_common_whitespace(ws_list)
        return ""

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        src_whitespace = self._get_source_whitespace(source)

        if isinstance(target, PatternMessage):
            trg_whitespace = self._get_whitespace(target.pattern)
            if trg_whitespace == src_whitespace:
                return
            yield self.report(context, self._make_msg(trg_whitespace, src_whitespace))
            return

        if isinstance(target, SelectMessage):
            for keys, tgt_pattern in target.variants.items():
                trg_whitespace = self._get_whitespace(tgt_pattern)
                if src_whitespace == trg_whitespace:
                    continue
                yield self.report(
                    context,
                    self._make_msg(
                        trg_whitespace, src_whitespace, _format_variant_keys(keys)
                    ),
                )
            return

    def _make_msg(
        self, trg_whitespace: str, src_whitespace: str, label: str = ""
    ) -> str:
        prefix = f"Variant [{label}]: " if label else ""
        return f"{prefix}{self._message} (expected {src_whitespace!r}, got {trg_whitespace!r})"


class LeadingWhitespaceMismatch(_WhitespaceMismatch):
    name: str = "leading-whitespace-mismatch"

    _message = f"Leading{_MESSAGE}"
    _whitespace_regex = _RE_LEADING_WHITESPACE

    def _iterate(self, object: list[Any]) -> Iterator[Any]:
        """Iterate forward through given object."""
        yield from object

    def _get_common_whitespace(self, whitespace_list: list[str]) -> str:
        """Longest common prefix for leading whitespace."""
        return commonprefix(whitespace_list)


class TrailingWhitespaceMismatch(_WhitespaceMismatch):
    name: str = "trailing-whitespace-mismatch"

    _message = f"Trailing{_MESSAGE}"
    _whitespace_regex = _RE_TRAILING_WHITESPACE

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.format_severities: dict[Format, Severity] = {
            Format.gettext: Severity.ERROR
        }

    def _iterate(self, object: list[Any]) -> Iterator[Any]:
        """Iterate backwards through given object."""
        yield from reversed(object)

    def _get_common_whitespace(self, whitespace_list: list[str]) -> str:
        """Longest common suffix for trailing whitespace."""
        reversed_ws = [ws[::-1] for ws in whitespace_list]
        return commonprefix(reversed_ws)[::-1]


def _format_variant_keys(keys: tuple[str | CatchallKey, ...]) -> str:
    parts = []
    for k in keys:
        if isinstance(k, CatchallKey):
            parts.append(k.value if k.value is not None else "*")
        else:
            parts.append(k)
    return ", ".join(parts)
