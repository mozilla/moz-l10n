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
from typing import Any, Iterator

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import (
    CatchallKey,
    Message,
    Pattern,
    PatternMessage,
    SelectMessage,
)

_MESSAGE = " whitespace mismatch"
_RE_LEADING_WHITESPACE = re.compile(r"^\s+")
_RE_TRAILING_WHITESPACE = re.compile(r"\s+$")


class _WhitespaceMismatch(Rule):
    family: str = "content"
    default_severity: Severity = Severity.WARNING
    _message: str = ""
    _whitespace_regex: re.Pattern[str]
    _pattern_index: int = 0

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
        step = self._pattern_index or 1
        for element in pattern[::step]:
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

        if match := self._whitespace_regex.search("".join(string_stack[::step])):
            return match[0]
        return ""

    def check(
        self, target: Message | None, source: Message | None, context: LintContext
    ) -> Iterator[Diagnostic]:
        if source is None or target is None:
            return

        if isinstance(target, PatternMessage) and isinstance(source, PatternMessage):
            trg_whitespace = self._get_whitespace(target.pattern)
            src_whitespace = self._get_whitespace(source.pattern)
            if trg_whitespace == src_whitespace:
                return
            yield self.report(self._make_msg(trg_whitespace, src_whitespace), context)
            return

        if isinstance(target, SelectMessage) and isinstance(source, PatternMessage):
            src_whitespace = self._get_whitespace(source.pattern)
            for keys, tgt_pattern in target.variants.items():
                trg_whitespace = self._get_whitespace(tgt_pattern)
                if src_whitespace == trg_whitespace:
                    continue
                yield self.report(
                    self._make_msg(
                        src_whitespace, trg_whitespace, _format_variant_keys(keys)
                    ),
                    context,
                )
            return

        if isinstance(target, SelectMessage) and isinstance(source, SelectMessage):
            source_variants_by_key = {
                _format_variant_keys(keys): pattern
                for keys, pattern in source.variants.items()
            }
            default_source_pattern = next(iter(source.variants.values()))
            for keys, tgt_pattern in target.variants.items():
                label = _format_variant_keys(keys)
                src_pattern = source_variants_by_key.get(label, default_source_pattern)
                trg_whitespace = self._get_whitespace(tgt_pattern)
                src_whitespace = self._get_whitespace(src_pattern)
                if trg_whitespace == src_whitespace:
                    continue
                yield self.report(
                    self._make_msg(trg_whitespace, src_whitespace, label), context
                )

    def _make_msg(
        self, trg_whitespace: str, src_whitespace: str, label: str = ""
    ) -> str:
        prefix = f"Variant [{label}]: " if label else ""
        return f"{prefix}{self._message} (expected {src_whitespace!r}, got {trg_whitespace!r})"


class LeadingWhitespaceMismatch(_WhitespaceMismatch):
    name: str = "leading-whitespace-mismatch"
    _message = f"Leading{_MESSAGE}"
    _whitespace_regex = _RE_LEADING_WHITESPACE
    _pattern_index = 0


class TrailingWhitespaceMismatch(_WhitespaceMismatch):
    name: str = "trailing-whitespace-mismatch"
    _message = f"Trailing{_MESSAGE}"
    _whitespace_regex = _RE_TRAILING_WHITESPACE
    _pattern_index = -1

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.format_severities: dict[Format, Severity] = {
            Format.gettext: Severity.ERROR
        }


def _format_variant_keys(keys: tuple[str | CatchallKey, ...]) -> str:
    parts = []
    for k in keys:
        if isinstance(k, CatchallKey):
            parts.append(k.value if k.value is not None else "*")
        else:
            parts.append(k)
    return ", ".join(parts)
