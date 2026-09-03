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
from moz.l10n.lint.tools import get_simple_preview
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
    message: str = ""
    default_severity: Severity = Severity.WARNING
    _whitespace_regex: re.Pattern[str]

    def _get_whitespaces(self, *messages: Message | Pattern) -> list[str]:
        results = []
        for msg in messages:
            preview = get_simple_preview(msg)
            # don't try to match "only whitespace"
            if not preview or not preview.strip():
                results.append("")
                continue
            match = self._whitespace_regex.search(preview)
            results.append(match.group(0) if match else "")
        return results

    def check(
        self, target: Message | None, source: Message | None, context: LintContext
    ) -> Iterator[Diagnostic]:
        if source is None or target is None:
            return

        if isinstance(target, PatternMessage) and isinstance(source, PatternMessage):
            trg_whitespace, src_whitespace = self._get_whitespaces(target, source)
            if trg_whitespace == src_whitespace:
                return
            yield self._report(trg_whitespace, src_whitespace, context)
            return

        if isinstance(target, SelectMessage) and isinstance(source, PatternMessage):
            src_whitespace = self._get_whitespaces(source)[0]
            for keys, tgt_pattern in target.variants.items():
                trg_whitespace = self._get_whitespaces(tgt_pattern)[0]
                if src_whitespace == trg_whitespace:
                    continue
                yield self._report(
                    src_whitespace, trg_whitespace, context, _format_variant_keys(keys)
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
                trg_whitespace, src_whitespace = self._get_whitespaces(
                    tgt_pattern, src_pattern
                )
                if trg_whitespace == src_whitespace:
                    continue
                yield self._report(trg_whitespace, src_whitespace, context, label)

    def _report(
        self,
        trg_whitespace: str,
        src_whitespace: str,
        context: LintContext,
        label: str | None = None,
    ) -> Diagnostic:
        prefix = f"Variant [{label}]: " if label else ""
        return self.diagnostic(
            f"{prefix}{self.message} (expected {trg_whitespace!r}, got {src_whitespace!r})",
            severity=context.severity_of(self),
        )


class LeadingWhitespaceMismatch(_WhitespaceMismatch):
    name: str = "leading-whitespace-mismatch"
    message = f"Leading{_MESSAGE}"
    _whitespace_regex = _RE_LEADING_WHITESPACE


class TrailingWhitespaceMismatch(_WhitespaceMismatch):
    name: str = "trailing-whitespace-mismatch"
    message = f"Trailing{_MESSAGE}"
    _whitespace_regex = _RE_TRAILING_WHITESPACE

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
