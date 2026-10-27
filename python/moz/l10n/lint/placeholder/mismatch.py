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
from collections import Counter
from dataclasses import dataclass
from typing import Iterator

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
        diff = _diff_messages(target, source, context.resource_format)
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
        diff = _diff_messages(target, source, context.resource_format)
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
        diff = _diff_messages(target, source, context.resource_format)
        for element in sorted(diff.extra_elements):
            yield self.report(context, f"Element {element} not found in reference")


class MissingElement(Rule):
    name = "missing-element"
    family = "placeholder"
    default_severity = Severity.WARNING

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        diff = _diff_messages(target, source, context.resource_format)
        for element in sorted(diff.missing_elements):
            yield self.report(context, f"Element {element} not found in translation")


_RE_PRINTF = re.compile(
    r"%#@\w+@|%(?:[1-9][0-9]*\$|<)?[-#+ 0,(]?[0-9.]*(?:hh?|ll?|[qztjLT])?.?"
)
"""Regex to match printf specifiers and Xcode stringsdict plural keys.
Includes positional (%1$s), argument reuse (%<s), flags (%-10.2f),
length modifiers (%ld), and iOS object specifiers (%@).
"""
_RE_REUSABLE = re.compile(r"%(?:[1-9][0-9]*\$|<|#@).*")
"""Regex to match tokens that can be reused freely without strict occurrence counts:
Positional indices: %1$s, Relative reuse: %<s, Xcode stringsdict keys: %#@items@.
"""
_RE_HTML_TAG = re.compile(r"<\s*(/?)\s*([A-Za-z_][\w:.-]*)(.*?)(/?)\s*>", re.DOTALL)
"""Regex to match HTML/XML tags with four capture groups:
- Group 1 (closing):      '/' for end tags (</tag>), otherwise empty
- Group 2 (name):         Tag name ('a', 'b', 'xliff:g')
- Group 3 (attributes):   Raw attribute string (' href="url"')
- Group 4 (self_closing): '/' for self-closing tags (<br />), otherwise empty
"""
_RE_WEBEXT = re.compile(r"\$[1-9][0-9]*|\$[A-Za-z0-9_]+\$")
"""Regex to match WebExtension placeholder syntax in plain text like
indexed placeholders ('$1', '$2') or named placeholders ('$FOO$', '$USER$')"""


@dataclass(frozen=True)
class _Mismatch:
    placeholder: str
    expected: int
    found: int


@dataclass
class _DiffResult:
    extra_placeholders: list[_Mismatch]
    missing_placeholders: list[_Mismatch]
    extra_elements: set[str]
    missing_elements: set[str]


@dataclass
class _PatternScan:
    """Scan a single variant pattern for markup elements and placeholders."""

    text: str
    elements: Counter[str]
    element_spans: list[tuple[int, int]]
    placeholders: list[str]
    ph_spans: list[tuple[int, int, str]]
    unnumbered_counts: Counter[str]

    def __init__(self, pattern: Pattern, is_printf_format: bool) -> None:
        self.text, self.ph_spans = _get_text_and_spans(pattern)
        mismatched = _get_mismatched_tag_spans(self.text)
        enclosed_spans: set[tuple[int, int, str]] = set()
        self.elements: Counter[str] = Counter()
        self.element_spans: list[tuple[int, int]] = []

        for match in _RE_HTML_TAG.finditer(self.text):
            if not _is_element(match, self.text) and match.span() not in mismatched:
                continue
            self.elements[match[0]] += 1
            self.element_spans.append(match.span())
            for start, end, val in self.ph_spans:
                if (
                    match.start() <= start
                    and end <= match.end()
                    and match.span() != (start, end)
                ):
                    enclosed_spans.add((start, end, val))

        self.placeholders = [
            val
            for start, end, val in self.ph_spans
            if (start, end, val) not in enclosed_spans
        ]
        self.unnumbered_counts = (
            _count_unnumbered_placeholders(self.text) if is_printf_format else Counter()
        )


def _diff_messages(
    target: Message, source: Message, resource_format: Format
) -> _DiffResult:
    is_printf_format = resource_format in (Format.android, Format.xliff)
    scan_printf = is_printf_format and not _has_literal_percent(source)

    source_required_ph: set[str] = set()
    source_elements: set[str] = set()
    source_elements_by_variant: list[Counter[str]] = []
    source_unnumbered_counts: list[Counter[str]] = []

    for _, pattern in source:
        source_scan = _PatternScan(pattern, scan_printf)
        source_elements.update(source_scan.elements)
        source_elements_by_variant.append(source_scan.elements)
        source_required_ph.update(source_scan.placeholders)
        if is_printf_format:
            source_unnumbered_counts.append(source_scan.unnumbered_counts)

    target_elements: set[str] = set()
    target_found_ph: set[str] = set()
    extra_placeholders: list[_Mismatch] = []
    target_unnumbered_counts: list[Counter[str]] = []

    literal_regexes: list[re.Pattern[str]] = []
    if scan_printf:
        literal_regexes.append(_RE_PRINTF)
    if resource_format is Format.webext:
        literal_regexes.append(_RE_WEBEXT)

    for _, pattern in target:
        target_scan = _PatternScan(pattern, is_printf_format)
        target_elements.update(target_scan.elements)
        if is_printf_format:
            target_unnumbered_counts.append(target_scan.unnumbered_counts)

        # Check expression-based placeholders
        for val in target_scan.placeholders:
            if val in source_required_ph:
                target_found_ph.add(val)
            else:
                extra_placeholders.append(_Mismatch(val, expected=0, found=1))

        # Check raw literal placeholders from plain text
        for regex in literal_regexes:
            for match in regex.finditer(target_scan.text):
                if match[0] in IGNORED_PLACEHOLDERS:
                    continue
                # Skip if already identified via AST Expression
                if any(
                    s <= match.start() and match.end() <= e
                    for s, e, _ in target_scan.ph_spans
                ):
                    continue
                # Skip if enclosed in markup
                if any(
                    start <= match.start() and match.end() <= end
                    for start, end in target_scan.element_spans
                ):
                    continue
                if match[0] in source_required_ph:
                    target_found_ph.add(match[0])
                else:
                    extra_placeholders.append(_Mismatch(match[0], expected=0, found=1))

    # Reusable & named placeholders diff
    missing_placeholders: list[_Mismatch] = []
    for ph in sorted(source_required_ph):
        if is_printf_format and not _is_reusable(ph):
            continue
        if ph not in target_found_ph:
            missing_placeholders.append(_Mismatch(ph, expected=1, found=0))

    # 3. Unnumbered printf occurrence checking (Android / XLIFF)
    missing_elements = source_elements - target_elements
    all_keys = {k for cnt in source_unnumbered_counts for k in cnt}
    if is_printf_format and all_keys:
        src_min = {k: min(cnt[k] for cnt in source_unnumbered_counts) for k in all_keys}
        src_max = {k: max(cnt[k] for cnt in source_unnumbered_counts) for k in all_keys}

        # Calculate suppression for placeholders enclosed in dropped elements
        missing_element_counts: Counter[str] = Counter()
        for i, variant_elements in enumerate(source_elements_by_variant):
            missing_in_var: Counter[str] = Counter()
            for el_name, count in variant_elements.items():
                if el_name in missing_elements:
                    for ph, occ in _count_unnumbered_placeholders(el_name).items():
                        missing_in_var[ph] += count * occ
            missing_element_counts = (
                missing_in_var if i == 0 else missing_element_counts & missing_in_var
            )

        for tgt_count in target_unnumbered_counts:
            for ph, maximum in src_max.items():
                minimum = src_min[ph]
                found = tgt_count[ph]
                if found > maximum:
                    extra_placeholders.append(_Mismatch(ph, maximum, found))
                elif found + missing_element_counts[ph] < minimum:
                    missing_placeholders.append(_Mismatch(ph, minimum, found))

    return _DiffResult(
        extra_placeholders=list(dict.fromkeys(extra_placeholders)),
        missing_placeholders=list(dict.fromkeys(missing_placeholders)),
        extra_elements=target_elements - source_elements,
        missing_elements=missing_elements,
    )


def _get_text_and_spans(pattern: Pattern) -> tuple[str, list[tuple[int, int, str]]]:
    """Serialize a pattern into raw text while tracking placeholder spans."""
    text = ""
    ph_spans: list[tuple[int, int, str]] = []

    for element in pattern:
        if isinstance(element, str):
            text += element

        elif isinstance(element, Markup):
            if element.kind == "close":
                text += f"</{element.name}>"
            else:
                options = ""
                if element.options:
                    opts = [
                        f'{key}="{value}"'
                        if isinstance(value, str)
                        else f"{key}=${value.name}"
                        for key, value in element.options.items()
                    ]
                    options = f" {' '.join(opts)}"
                suffix = " />" if element.kind == "standalone" else ">"
                text += f"<{element.name}{options}{suffix}"

        elif isinstance(element, Expression):
            if element.function == "html" and isinstance(element.arg, str):
                text += element.arg
            elif isinstance(src := element.attributes.get("source"), str):
                if src not in IGNORED_PLACEHOLDERS:
                    ph_spans.append((len(text), len(text) + len(src), src))
                text += src
            elif element.function == "entity" and isinstance(element.arg, VariableRef):
                name = element.arg.name
                ph_spans.append((len(text), len(text) + len(name), name))
                text += name
            elif isinstance(element.arg, VariableRef):
                var_name = f"${element.arg.name}"
                ph_spans.append((len(text), len(text) + len(var_name), var_name))
                text += var_name
            elif element.arg:
                val = str(element.arg)
                if val not in IGNORED_PLACEHOLDERS:
                    ph_spans.append((len(text), len(text) + len(val), val))
                text += val

    return text, ph_spans


def _count_unnumbered_placeholders(text: str) -> Counter[str]:
    return Counter(
        match[0]
        for match in _RE_PRINTF.finditer(text)
        if match[0] not in IGNORED_PLACEHOLDERS and not _is_reusable(match[0])
    )


def _is_reusable(token: str) -> bool:
    """Check if a placeholder may appear multiple times.

    Positional printf specifiers ('%1$s', '%#@items@') and named variables
    can be repeated freely. Unnumbered specifiers ('%s', '%@') consume arguments
    in order and must match source occurrence counts.
    """
    if token.startswith("%"):
        return bool(_RE_REUSABLE.fullmatch(token))
    return True


def _has_literal_percent(message: Message) -> bool:
    """Check if any plain text element in the message contains a literal '%'."""
    for _, pattern in message:
        for element in pattern:
            if isinstance(element, str) and "%" in element:
                return True
    return False


def _is_element(match: re.Match[str], context: str) -> bool:
    closing, name, attributes, self_closing = match.groups()
    if self_closing or attributes.strip():
        return True
    pair = (
        rf"<\s*{re.escape(name)}\s*(?:/?>|\s)"
        if closing
        else rf"</\s*{re.escape(name)}\s*>"
    )
    return re.search(pair, context) is not None


def _get_mismatched_tag_spans(context: str) -> set[tuple[int, int]]:
    """Find spans of tags whose nesting doesn't line up, as in '<a>text</b>'."""
    open_tags: list[tuple[str, tuple[int, int]]] = []
    mismatched: set[tuple[int, int]] = set()
    for match in _RE_HTML_TAG.finditer(context):
        closing, name, attributes, self_closing = match.groups()
        if self_closing or attributes.strip():
            continue

        span = match.span()
        if not closing:
            open_tags.append((name, span))
        elif open_tags and open_tags[-1][0] == name:
            open_tags.pop()
        else:
            # Unclosed tags on their own are ambiguous (<Enter>).
            # Only collect when an open and close tag collides.
            mismatched.add(span)
            if open_tags:
                mismatched.add(open_tags.pop()[1])
    return mismatched
