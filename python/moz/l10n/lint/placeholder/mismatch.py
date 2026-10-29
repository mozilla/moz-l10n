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
from dataclasses import dataclass
from typing import Iterator, Literal, NamedTuple

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import Expression, Markup, Message, Pattern, VariableRef

IGNORED_PLACEHOLDERS = {"%%", "%n"}


class ExtraPlaceholder(Rule):
    name = "extra"
    family = "placeholder"
    default_severity = Severity.ERROR

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        diff = _DiffResult(target, source, context.resource_format)
        for mismatch in diff.extra_placeholders:
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
        diff = _DiffResult(target, source, context.resource_format)
        for mismatch in diff.missing_placeholders:
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
        diff = _DiffResult(target, source, context.resource_format)
        for element in sorted(diff.extra_elements):
            yield self.report(context, f"Element {element} not found in reference")


class MissingElement(Rule):
    name = "missing-element"
    family = "placeholder"
    default_severity = Severity.WARNING

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        diff = _DiffResult(target, source, context.resource_format)
        for element in sorted(diff.missing_elements):
            yield self.report(context, f"Element {element} not found in translation")


@dataclass(frozen=True)
class _Mismatch:
    placeholder: str
    expected: int
    found: int


class _DiffResult:
    extra_placeholders: list[_Mismatch]
    missing_placeholders: list[_Mismatch]
    extra_elements: set[_MarkupKey]
    missing_elements: set[_MarkupKey]

    def __init__(
        self, target: Message, source: Message, resource_format: Format
    ) -> None:
        is_printf_format = resource_format in (Format.android, Format.xliff)

        src_scans = [_PatternScan(p, is_printf_format) for _, p in source]
        trg_scans = [_PatternScan(p, is_printf_format) for _, p in target]
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

        if is_printf_format and src_scans and trg_scans:
            self._collect_placeholders(src_scans, trg_scans)

    def _collect_placeholders(
        self, src_scans: list[_PatternScan], trg_scans: list[_PatternScan]
    ) -> None:
        # Suppression intersection across source variants
        suppressed: Counter[str] = Counter()
        for i, scan in enumerate(src_scans):
            var_supp = Counter(
                option_value
                for el in scan.elements & self.missing_elements
                for _, option_value in el.options
                if not _is_reusable(option_value)
            )
            suppressed = var_supp if i == 0 else suppressed & var_supp

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

    def __init__(self, pattern: Pattern, is_printf: bool) -> None:
        self.elements: set[_MarkupKey] = set()
        self.reusable: set[str] = set()
        self.unnumbered: Counter[str] = Counter()

        def record_token(token: str | None) -> None:
            if not token or token in IGNORED_PLACEHOLDERS:
                return
            if is_printf and not _is_reusable(token):
                self.unnumbered[token] += 1
            else:
                self.reusable.add(token)

        def record_option_token(val: str | VariableRef) -> None:
            """Record markup attribute values.

            Attributes are already validated via _MarkupKey.
            Only unnumbered printf (%s, %@) affect sequential runtime
            argument indexing and need to be tracked in unnumbered.
            """
            if not is_printf or not isinstance(val, str):
                return
            if (
                not val.startswith("%")
                or val in IGNORED_PLACEHOLDERS
                or _is_reusable(val)
            ):
                return
            self.unnumbered[val] += 1

        candidates: list[_MarkupKey] = []
        for node in pattern:
            if isinstance(node, Markup):
                candidates.append(_MarkupKey.from_markup(node))
                for value in node.options.values():
                    record_option_token(value)

            elif isinstance(node, Expression):
                if node.function == "html":
                    if key := _MarkupKey.from_expression(node):
                        candidates.append(key)
                        for _, opt_val in key.options:
                            record_option_token(opt_val)
                else:
                    record_token(_get_expression_token(node))

        has_closing = any(el.kind == "close" for el in candidates)
        self.elements = {
            el for el in candidates if el.kind != "open" or el.options or has_closing
        }


class _MarkupKey(NamedTuple):
    """Hashable markup representation for sets and counters."""

    kind: Literal["open", "standalone", "close"]
    name: str
    options: tuple[tuple[str, str], ...] = ()

    def __str__(self) -> str:
        if self.kind == "close":
            return f"</{self.name}>"
        opts_str = "".join(f' {k}="{v}"' for k, v in self.options)
        closer = "/" if self.kind == "standalone" else ""
        return f"<{self.name}{opts_str}{closer}>"

    @classmethod
    def from_markup(cls, node: Markup) -> "_MarkupKey":
        options = tuple(
            sorted(
                (k, v.name if isinstance(v, VariableRef) else v)
                for k, v in node.options.items()
            )
        )
        return cls(node.kind, node.name, options)

    @classmethod
    def from_expression(cls, node: Expression) -> "_MarkupKey" | None:
        if not isinstance(node.arg, str):
            return None
        arg = node.arg.strip()
        if not (arg.startswith("<") and arg.endswith(">")):
            return None
        if arg.startswith("</"):
            name = arg[2:-1].strip()
            return cls("close", name) if name else None

        kind: Literal["open", "standalone", "close"]
        kind, content = (
            ("standalone", arg[1:-2]) if arg.endswith("/>") else ("open", arg[1:-1])
        )
        parts = content.split(None, 1)
        if not parts:
            return None
        # collect tag options if any
        options = tuple(
            sorted(
                (k, v.strip("\"'"))
                for token in (parts[1].split() if len(parts) > 1 else ())
                if "=" in token
                for k, v in [token.split("=", 1)]
            )
        )
        return cls(kind, parts[0], tuple(sorted(options)))


def _get_expression_token(node: Expression) -> str | None:
    """Extract a hashable/comparable token string from `Expression`.
    Note:
    * `{$user}` This is a runtime variable! We pass the `$`
    * `{$brand :entity}` This is an entity reference! We drop the `$`
    """
    if "source" in node.attributes:
        return str(node.attributes["source"]).strip("|")
    if isinstance(node.arg, str):
        return node.arg
    if isinstance(node.arg, VariableRef):
        return node.arg.name if node.function == "entity" else f"${node.arg.name}"
    return None


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
