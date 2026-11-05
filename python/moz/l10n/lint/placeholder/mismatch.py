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

    _last_source: Message | None = None
    _last_target: Message | None = None
    _last_format: Format | None = None
    _last_result: _Diff | None = None

    @classmethod
    def cached(cls, target: Message, source: Message, context: LintContext) -> _Diff:
        if (
            source is not cls._last_source
            or target is not cls._last_target
            or context.resource_format is not cls._last_format
            or cls._last_result is None
        ):
            cls._last_source = source
            cls._last_target = target
            cls._last_format = context.resource_format
            cls._last_result = cls(target, source, context)
        return cls._last_result

    def __init__(self, target: Message, source: Message, context: LintContext) -> None:
        src_scans = [_PatternScan(p, context.is_printf) for _, p in source]
        trg_scans = [_PatternScan(p, context.is_printf) for _, p in target]
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
        self.elements = set()
        self.reusable = set()
        self.unnumbered = Counter()

        candidates: list[_MarkupKey] = []
        """All markup to filter for bare open tags (e.g. <br>, <img>)
        which requires inspecting the whole pattern."""
        for node in pattern:
            if isinstance(node, Markup):
                candidates.append(_MarkupKey.from_markup(node))
                if is_printf:
                    self._record_option_tokens(node.options.values())

            elif isinstance(node, Expression):
                if node.function == "html":
                    if key := _MarkupKey.from_expression(node):
                        candidates.append(key)
                        if is_printf:
                            self._record_option_tokens(v for _, v in key.options)
                elif token := _get_expression_token(node):
                    if _is_reusable(token) or not is_printf:
                        self.reusable.add(token)
                    else:
                        self.unnumbered[token] += 1

        # Track opening tags without options as lint-able elements
        # only if accompanied by closing tags or option attributes.
        has_closing = any(el.kind == "close" for el in candidates)
        self.elements = {
            el for el in candidates if el.kind != "open" or el.options or has_closing
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


class _MarkupKey(NamedTuple):
    """Hashable markup representation for sets and counters.
    * Created from both `Markup` and `Expression(function="html",...`
      which are not hashable and cannot be used in set math.
    * Sorts options so `<x x="x" y="y">` == `<x y="y" x="x">`.
    """

    kind: Literal["open", "standalone", "close"]
    name: str
    options: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_markup(cls, node: Markup) -> _MarkupKey:
        options = tuple(
            sorted(
                (k, f"${v.name}" if isinstance(v, VariableRef) else v)
                for k, v in node.options.items()
            )
        )
        return cls(node.kind, node.name, options)

    @classmethod
    def from_expression(cls, node: Expression) -> _MarkupKey | None:
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
        return cls(kind, parts[0], options)

    def __str__(self) -> str:
        """Convenience stringification for reporting."""
        if self.kind == "close":
            return f"</{self.name}>"
        opts_str = "".join(f' {k}="{v}"' for k, v in self.options)
        closer = "/" if self.kind == "standalone" else ""
        return f"<{self.name}{opts_str}{closer}>"


def _get_expression_token(node: Expression) -> str | None:
    """Get a hashable/comparable token string from `Expression`.
    `serialize_message(format, [node])` would work sometimes but:
    * MF2 syntax leakage: `{$user}, {$brand :entity}, {42}` instead of: `$user, brand, 42`
    * For XLIFF instead of `Name` we'd get a full namespace wrapper:
      `<xliff:g xmlns:xliff="urn:..." id="a">Name</xliff:g>`
    * `ValueError: Unsupported expression: Expression(None, function='current_date')`

    Note:
    * `{$user}` This is a runtime variable! We pass the `$`
    * `{$brand :entity}` This is an entity reference! We drop the `$`
    """
    if "source" in node.attributes:
        token = str(node.attributes["source"]).strip("|")
    elif isinstance(node.arg, str):
        token = node.arg
    elif isinstance(node.arg, VariableRef):
        token = node.arg.name if node.function == "entity" else f"${node.arg.name}"
    else:
        return None
    return token if token not in IGNORED_PLACEHOLDERS else None


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
