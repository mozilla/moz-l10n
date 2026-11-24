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

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, NamedTuple

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.message import serialize_message
from moz.l10n.model import Expression, Markup, Message, Pattern, VariableRef

IGNORED_PLACEHOLDERS = {"%%", "%n"}


class ExtraPlaceholder(Rule):
    name = "extra"
    family = "placeholder"
    default_severity = Severity.ERROR

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for mismatch in _Diff.cached(target, source, context).extra_placeholders:
            if mismatch.expected == 0:
                msg = f"Placeholder {mismatch.placeholder} not found in reference"
            else:
                msg = (
                    f"Placeholder {mismatch.placeholder} has more occurrences in translation "
                    f"(expected {mismatch.expected}, found {mismatch.found})"
                )
            yield self.report(context, msg)


class MissingPlaceholder(Rule):
    name = "missing"
    family = "placeholder"
    default_severity = Severity.WARNING

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for mismatch in _Diff.cached(target, source, context).missing_placeholders:
            if mismatch.found == 0:
                msg = f"Placeholder {mismatch.placeholder} not found in translation"
            else:
                msg = (
                    f"Placeholder {mismatch.placeholder} has fewer occurrences in translation "
                    f"(expected {mismatch.expected}, found {mismatch.found})"
                )
            yield self.report(context, msg)


class ExtraElement(Rule):
    name = "extra-element"
    family = "placeholder"
    default_severity = Severity.ERROR

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for element in sorted(_Diff.cached(target, source, context).extra_elements):
            yield self.report(context, f"Element {element} not found in reference")


class MissingElement(Rule):
    name = "missing-element"
    family = "placeholder"
    default_severity = Severity.WARNING

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for element in sorted(_Diff.cached(target, source, context).missing_elements):
            yield self.report(context, f"Element {element} not found in translation")


@dataclass(frozen=True)
class _Mismatch:
    placeholder: str
    expected: int
    found: int


class _Diff:
    extra_placeholders: list[_Mismatch]
    missing_placeholders: list[_Mismatch]
    extra_elements: set[_MarkupKey]
    missing_elements: set[_MarkupKey]

    _cache_key: tuple[Message, Message, Format] | None = None
    _last_result: _Diff | None = None

    @classmethod
    def cached(cls, target: Message, source: Message, context: LintContext) -> _Diff:
        if (
            cls._last_result is None
            or (source, target, context.resource_format) != cls._cache_key
        ):
            cls._cache_key = (source, target, context.resource_format)
            cls._last_result = cls(target, source, context)
        return cls._last_result

    def __init__(self, target: Message, source: Message, context: LintContext) -> None:
        src_scans = [_PatternScan(p, context) for _, p in source]
        trg_scans = [_PatternScan(p, context) for _, p in target]
        src_elements = {el for s in src_scans for el in s.elements}
        trg_elements = {el for s in trg_scans for el in s.elements}

        self.missing_elements = src_elements - trg_elements
        self.extra_elements = trg_elements - src_elements
        src_reusable = {ph for s in src_scans for ph in s.reusable}
        trg_reusable = {ph for s in trg_scans for ph in s.reusable}
        self.missing_placeholders = [
            _Mismatch(ph, expected=1, found=0)
            for ph in sorted(src_reusable - trg_reusable)
        ]
        self.extra_placeholders = [
            _Mismatch(ph, expected=0, found=1)
            for ph in sorted(trg_reusable - src_reusable)
        ]

        if context.is_printf and src_scans and trg_scans:
            self._collect_placeholders(src_scans, trg_scans)

    def _collect_placeholders(
        self, src_scans: list[_PatternScan], trg_scans: list[_PatternScan]
    ) -> None:
        # avoid redundant reports for placeholders inside missing elements
        suppressed: Counter[str] = Counter()
        for scan in src_scans:
            suppressed.update(
                Counter(
                    option_value
                    for el in scan.elements & self.missing_elements
                    for _, option_value in el.options
                    if not _is_reusable(option_value)
                )
            )

        # Compare aggregate bounds deterministically (at most 1 report per token)
        all_src_ph = {ph for s in src_scans for ph in s.unnumbered}
        all_trg_ph = {ph for s in trg_scans for ph in s.unnumbered}
        for ph in sorted(all_src_ph):
            src_counts = [s.unnumbered[ph] for s in src_scans]
            trg_counts = [s.unnumbered[ph] for s in trg_scans]
            src_min, src_max = min(src_counts), max(src_counts)
            trg_min, trg_max = min(trg_counts), max(trg_counts)

            if trg_max > src_max:
                self.extra_placeholders.append(_Mismatch(ph, src_max, trg_max))
            elif trg_min + suppressed[ph] < src_min:
                self.missing_placeholders.append(_Mismatch(ph, src_min, trg_min))

        # Tokens in target that never existed in source
        for ph in sorted(all_trg_ph - all_src_ph):
            trg_max = max(s.unnumbered[ph] for s in trg_scans)
            self.extra_placeholders.append(_Mismatch(ph, expected=0, found=trg_max))


class _PatternScan:
    """Collection for a single variant pattern for markup elements and placeholders."""

    elements: set[_MarkupKey]
    reusable: set[str]
    unnumbered: Counter[str]

    def __init__(self, pattern: Pattern, context: LintContext) -> None:
        self.elements = set()
        self.reusable = set()
        self.unnumbered = Counter()

        candidates: list[_MarkupKey] = []
        """All markup to filter for bare open tags (e.g. <br>, <img>)
        which requires inspecting the whole pattern."""
        for node in pattern:
            if isinstance(node, Markup):
                candidates.append(_MarkupKey.from_markup(node))
                if context.is_printf:
                    self._record_option_tokens(node.options.values())

            elif isinstance(node, Expression):
                token = serialize_message(context.resource_format, [node])
                if not token or token in IGNORED_PLACEHOLDERS:
                    continue
                if context.is_printf and not _is_reusable(token):
                    self.unnumbered[token] += 1
                else:
                    self.reusable.add(token)

        # Track opening tags without options as lint-able elements
        # only if accompanied by closing tags or option attributes.
        has_closing = any(el.kind is _MarkupKind.close for el in candidates)
        self.elements = {
            el
            for el in candidates
            if el.kind is not _MarkupKind.open or el.options or has_closing
        }

    def _record_option_tokens(self, values: Iterable[str | VariableRef]) -> None:
        """Record unnumbered printf specifiers in markup attributes.
        These are always `str` and never `VariableRef`. We ignore these by design.
        For example:
            `Please click <a href="%s">here</a> or see %s.`
        Our Android/XLIFF parsers keep the literal `%s` not `VariableRef` like:
            `Markup('open','a',options={'href': '%s'})`
        So we track them in `self.unnumbered` along text specifiers.
        See `test_extra_unnumbered_placeholder_with_markup_attribute`.
        """
        for value in values:
            if (
                isinstance(value, str)
                and value.startswith("%")
                and value not in IGNORED_PLACEHOLDERS
                and not _is_reusable(value)
            ):
                self.unnumbered[value] += 1


class _MarkupKind(Enum):
    open = 0
    standalone = 1
    close = 2

    def __lt__(self, other: object) -> bool:
        if isinstance(other, _MarkupKind):
            return self.value < other.value
        raise NotImplementedError


class _MarkupKey(NamedTuple):
    """Hashable markup representation to be used in sets and counters.

    `serialize_message` would make open+close pairs from single `open` or `standalone`
    and break on single `close` Markups. We would lose structured `options` that we use
    to sort out stray single Markup (`<Enter>`) and handle suppression of redundant reports.
    """

    name: str
    kind: _MarkupKind
    options: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_markup(cls, node: Markup) -> _MarkupKey:
        options = (
            (k, f"${v.name}" if isinstance(v, VariableRef) else v)
            for k, v in node.options.items()
        )
        return cls(node.name, _MarkupKind[node.kind], tuple(sorted(options)))

    def __str__(self) -> str:
        """Convenience stringification for reporting."""
        if self.kind is _MarkupKind.close:
            return f"</{self.name}>"
        opts_str = "".join(f' {k}="{v}"' for k, v in self.options)
        closer = "/" if self.kind is _MarkupKind.standalone else ""
        return f"<{self.name}{opts_str}{closer}>"


def _is_reusable(token: str) -> bool:
    """Check if a placeholder may appear multiple times.

    Positional printf specifiers ('%1$s', '%#@items@') and named variables
    can be repeated freely.
    Unnumbered specifiers ('%s', '%@') consume arguments in order
    and must match source occurrence counts.
    """
    if not token.startswith("%"):
        return True
    prefix, sep, _ = token[1:].partition("$")
    return (sep == "$" and prefix.isdigit()) or token.startswith("%#@")
