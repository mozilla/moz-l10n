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
from typing import Any, ClassVar, Iterable

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import CatchallKey, Message, Pattern, PatternMessage

_MESSAGE = " whitespace mismatch"


class _WhitespaceMismatch(Rule):
    family: str = "content"
    default_severity: Severity = Severity.WARNING

    _message: str = ""
    _whitespace_regex: re.Pattern[str]

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        # TODO: This needs dissolving when iterable Messages arrive!
        variants: Iterable[tuple[tuple[str | CatchallKey, ...], Pattern]]
        if isinstance(target, PatternMessage):
            variants = [((), target.pattern)]
        else:
            variants = target.variants.items()

        src_whitespace = self._get_source_whitespace(source)
        for keys, trg_pattern in variants:
            trg_whitespace = self._get_whitespace(trg_pattern)
            if trg_whitespace == src_whitespace:
                continue
            yield self.report(
                context, self._make_msg(trg_whitespace, src_whitespace, keys)
            )
        return

    def _iterate(self, list_object: Sequence[Any]) -> Iterator[str]:
        """Iterate forward or backward depending on Rule implementation."""
        raise NotImplementedError()

    # def _get_whitespace(self, pattern: Pattern) -> str:
    #     raise NotImplementedError()

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
            # collect elements that are ALL whitespace
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

    def _get_source_whitespace(self, source: Message) -> str:
        """Determine expected source whitespace as **single** baseline value from any variant."""
        if isinstance(source, PatternMessage):
            return self._get_whitespace(source.pattern)

        ws_list = [self._get_whitespace(p) for p in source.variants.values()]
        if not ws_list:
            return ""
        return commonprefix(list(self._iterate(ws_list)))

    def _make_msg(
        self,
        trg_whitespace: str,
        src_whitespace: str,
        keys: tuple[str | CatchallKey, ...],
    ) -> str:
        label = ", ".join(
            (k.value if k.value is not None else "*")
            if isinstance(k, CatchallKey)
            else k
            for k in keys
        )
        prefix = f"Variant [{label}]: " if label else ""
        return f"{prefix}{self._message} (expected {src_whitespace!r}, got {trg_whitespace!r})"


class LeadingWhitespaceMismatch(_WhitespaceMismatch):
    name: str = "leading-whitespace-mismatch"

    _message = f"Leading{_MESSAGE}"
    _whitespace_regex = re.compile(r"\s*")

    def _iterate(self, list_object: Sequence[Any]) -> Iterator[str]:
        """Iterate forward through given `list_object`."""
        yield from list_object

    # def _get_whitespace(self, pattern: Pattern) -> str:
    #     res = ""
    #     for part in pattern:
    #         if not isinstance(part, str) or (part and not part[0].isspace()):
    #             break
    #         res += part

    #     if res and (match := self._whitespace_regex.search(res)):
    #         if match[0] == res:
    #             return ""
    #         return match[0]
    #     return ""


class TrailingWhitespaceMismatch(_WhitespaceMismatch):
    name: str = "trailing-whitespace-mismatch"
    format_severities: ClassVar[dict[Format, Severity]] = {
        Format.gettext: Severity.ERROR
    }

    _message = f"Trailing{_MESSAGE}"
    _whitespace_regex = re.compile(r"\s*$")

    def _iterate(self, list_object: Sequence[Any]) -> Iterator[str]:
        """Iterate backwards through given `list_object`."""
        yield from reversed(list_object)

    # def _get_whitespace(self, pattern: Pattern) -> str:
    #     res = ""
    #     for part in reversed(pattern):
    #         if not isinstance(part, str) or (part and not part[-1].isspace()):
    #             break
    #         res = part + res
    #     if res and (match := self._whitespace_regex.search(res)):
    #         if match[0] == res:
    #             return ""
    #         return match[0]
    #     return ""
