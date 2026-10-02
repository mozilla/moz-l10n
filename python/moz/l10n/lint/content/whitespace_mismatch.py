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
from typing import Literal

from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import CatchallKey, Message, Pattern, PatternMessage


class WhitespaceMismatch(Rule):
    family: str = "content"
    name: str = "whitespace-mismatch"
    default_severity: Severity = Severity.WARNING

    _directions: Literal["start", "end", "both"]
    _message: str = ""
    _whitespace_regex: re.Pattern[str]

    def __init__(self, directions: Literal["start", "end", "both"] = "both") -> None:
        super()
        self._directions = directions

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        src_start_ws = _message_whitespace(source, "start")
        src_end_ws = _message_whitespace(source, "end")

        variants = (
            [((), target.pattern)]
            if isinstance(target, PatternMessage)
            else target.variants.items()
        )
        for keys, pattern in variants:
            if self._directions in ("start", "both"):
                tgt_start_ws = _pattern_start_whitespace(pattern)
                if tgt_start_ws != src_start_ws:
                    yield self.report(
                        context,
                        self._make_msg("start", tgt_start_ws, src_start_ws, keys),
                    )
                    continue
            if self._directions in ("end", "both"):
                tgt_end_ws = _pattern_end_whitespace(pattern)
                if tgt_end_ws != src_start_ws:
                    yield self.report(
                        context, self._make_msg("end", tgt_end_ws, src_end_ws, keys)
                    )

    def _make_msg(
        self,
        dir: Literal["start", "end"],
        trg_whitespace: str,
        src_whitespace: str,
        keys: tuple[str | CatchallKey, ...],
    ) -> str:
        prefix = f"Variant [{', '.join(str(k) or '*' for k in keys)}]: " if keys else ""
        msg = (
            "Leading whitespace mismatch"
            if dir == "start"
            else "Trailing whitespace mismatch"
        )
        return f"{prefix}{msg} (expected {src_whitespace!r}, got {trg_whitespace!r})"


def _message_whitespace(msg: Message, dir: Literal["start", "end"]) -> str:
    variants = (
        [((), msg.pattern)] if isinstance(msg, PatternMessage) else msg.variants.items()
    )

    if dir == "start":
        ws_list = [_pattern_start_whitespace(p) for _, p in variants]
        return commonprefix(ws_list) if ws_list else ""
    else:
        ws_rev_list = [_pattern_end_whitespace(p)[::-1] for _, p in variants]
        return commonprefix(ws_rev_list)[::-1] if ws_rev_list else ""


def _pattern_start_whitespace(pattern: Pattern) -> str:
    res = ""
    for part in pattern:
        if not isinstance(part, str) or (part and not part[0].isspace()):
            break
        res += part
    if res and (match := re.match(r"\s*", res)):
        return match[0]
    return ""


def _pattern_end_whitespace(pattern: Pattern) -> str:
    res = ""
    for part in reversed(pattern):
        if not isinstance(part, str) or (part and not part[-1].isspace()):
            break
        res = part + res
    if res and (match := re.search(r"\s*$", res)):
        return match[0]
    return ""
