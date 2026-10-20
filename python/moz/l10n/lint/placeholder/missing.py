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

import json
import re
from dataclasses import dataclass, field
from typing import Iterator

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import (
    CatchallKey,
    Expression,
    Markup,
    Message,
    Pattern,
    PatternMessage,
    SelectMessage,
    VariableRef,
)

IGNORED_PLACEHOLDERS = {"%%", "%n"}


class ExtraPlaceholder(Rule):
    name = "extra"
    family = "placeholder"
    default_severity = Severity.ERROR

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for placeholder in _get_matches(target, source, context).extra_placeholders:
            yield self.report(
                context, f"Placeholder {placeholder} not found in reference"
            )


class MissingPlaceholder(Rule):
    name = "missing"
    family = "placeholder"
    default_severity = Severity.WARNING

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for placeholder in _get_matches(target, source, context).missing_placeholders:
            yield self.report(
                context, f"Placeholder {placeholder} not found in translation"
            )


class ExtraElement(Rule):
    name = "extra-element"
    family = "placeholder"
    default_severity = Severity.ERROR

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for element in _get_matches(target, source, context).extra_elements:
            yield self.report(context, f"Element {element} not found in reference")


class MissingElement(Rule):
    name = "missing-element"
    family = "placeholder"
    default_severity = Severity.WARNING

    def check(
        self, target: Message, source: Message, context: LintContext
    ) -> Iterator[Diagnostic]:
        for element in _get_matches(target, source, context).missing_elements:
            yield self.report(context, f"Element {element} not found in translation")


@dataclass(frozen=True)
class _Matches:
    """The outcome of comparing a translation's placeholders against its source."""

    extra_placeholders: list[str] = field(default_factory=list)
    """Placeholders used by the translation that the source does not declare."""

    missing_placeholders: list[str] = field(default_factory=list)
    """Placeholders declared by the source that the translation does not use."""

    extra_elements: list[str] = field(default_factory=list)
    """Elements used by the translation that the source does not declare."""

    missing_elements: list[str] = field(default_factory=list)
    """Elements declared by the source that the translation does not use."""


def _get_matches(target: Message, source: Message, context: LintContext) -> _Matches:
    """
    Compare placeholders of `translation` against `source` ones.

    Both sides are flattened back to their format-native spelling first, so a
    placeholder typed out literally by the translator matches a source
    placeholder carrying the same `@source` attribute.
    """
    if cached := _PatternCache.get(target, source, context.resource_format):
        return cached

    source_placeholders = _source_placeholders(source)
    if source_placeholders is None:
        return _PatternCache.set(
            target, source, context.resource_format, _PatternCache.no_match
        )

    extra_elements: list[str] = []
    extra_placeholders: list[str] = []
    found: set[str] = set()
    for _, pattern in target:
        preview = _get_simple_preview(pattern)
        for match in _iter_placeholders(preview, context.resource_format):
            for placeholder in source_placeholders:
                if preview.startswith(placeholder, match.start()):
                    found.add(placeholder)
                    break
            else:
                if match[0] in IGNORED_PLACEHOLDERS:
                    continue
                if match[0].startswith("<"):
                    extra_elements.append(match[0])
                else:
                    extra_placeholders.append(match[0])

    missing = source_placeholders - found
    return _PatternCache.set(
        target,
        source,
        context.resource_format,
        _Matches(
            extra_placeholders=extra_placeholders,
            missing_placeholders=sorted(x for x in missing if not x.startswith("<")),
            extra_elements=extra_elements,
            missing_elements=sorted(x for x in missing if x.startswith("<")),
        ),
    )


def _source_placeholders(source: Message) -> set[str] | None:
    """Get set of format-native spelling of placeholders in `source`.

    Return `None` when it contains a bare `%` in its text.
    Such a message is probably not printf-formatted,
    scanning it for printf specifiers would only produce noise.
    """
    placeholders: set[str] = set()
    for _, pattern in source:
        for el in pattern:
            if isinstance(el, str):
                if "%" in el:
                    return None

            elif isinstance(el, (Expression, Markup)):
                placeholders.add(_preview_placeholder(el))

    return placeholders


class _PatternCache:
    """Hold match for 1 set of given messages.
    To keep us from re-scanning the same messages on the very next check.
    """

    last_target: Message | None = None
    last_source: Message | None = None
    last_format: Format | None = None
    last_match: _Matches = _Matches()
    no_match: _Matches = last_match

    @classmethod
    def get(
        cls, target: Message, source: Message, resource_format: Format
    ) -> _Matches | None:
        if (
            cls.last_target is target
            and cls.last_source is source
            and cls.last_format is resource_format
        ):
            return cls.last_match
        return None

    @classmethod
    def set(
        cls, target: Message, source: Message, resource_format: Format, match: _Matches
    ) -> _Matches:
        cls.last_target = target
        cls.last_source = source
        cls.last_format = resource_format
        cls.last_match = match
        return match


def _as_simple_pattern(msg: Message | Pattern) -> Pattern:
    """The single pattern of `msg`, selecting the fallback variant if it has several."""
    if isinstance(msg, PatternMessage):
        return msg.pattern
    if isinstance(msg, SelectMessage):
        return next(
            pattern
            for keys, pattern in msg.variants.items()
            if all(isinstance(key, CatchallKey) for key in keys)
        )
    return msg


def _get_simple_preview(msg: Message | Pattern) -> str:
    """Flatten an AST message or pattern into its format-native text representation."""
    pattern = _as_simple_pattern(msg)
    return "".join(_preview_placeholder(part) for part in pattern)


def _preview_placeholder(part: str | Expression | Markup) -> str:
    """Render a single pattern element as it was spelled in the original format."""
    if isinstance(part, str):
        return part
    if isinstance(ps := part.attributes.get("source", None), str):
        return ps
    if isinstance(part, Expression):
        if part.function == "html" and isinstance(part.arg, str):
            return part.arg
        elif part.function == "entity" and isinstance(part.arg, VariableRef):
            return part.arg.name
    elif part.kind in ("open", "standalone"):
        res = "<" + part.name
        for name, val in part.options.items():
            value_str = json.dumps(val) if isinstance(val, str) else "$" + val.name
            res += f" {name}={value_str}"
        res += ">" if part.kind == "open" else " />"
        return res
    elif part.kind == "close" and not part.options:
        return f"</{part.name}>"

    raise ValueError(f'Unable to handle placeholder string "{part}"')


# Placeholder matching regex patterns
_MARKUP = r"<[^>]+>"
_PRINTF = r"%(?:[1-9]\$)?[-#+ 0,(]?[0-9.]*(?:hh?|ll?|[qztjLT])?.?"
_ANDROID_PLURAL = r"%#@\w+@"
_WEBEXT = r"\$[a-zA-Z0-9_]+\$?"

_RE_MAP: dict[str, re.Pattern[str]] = {
    "android": re.compile(f"{_MARKUP}|{_ANDROID_PLURAL}|{_PRINTF}"),
    "gettext": re.compile(f"{_MARKUP}|{_PRINTF}"),
    "webext": re.compile(f"{_MARKUP}|{_WEBEXT}"),
}
# Fallback for generic/unknown formats
_RE_DEFAULT = re.compile(f"{_MARKUP}|{_PRINTF}|{_WEBEXT}")
"""Match all HTML/XML elements and Android & Xcode printf specifiers."""


def _iter_placeholders(text: str, resource_format: Format) -> Iterator[re.Match[str]]:
    """Get a regex iterable yielding matches if any."""
    return _RE_MAP.get(resource_format.name, _RE_DEFAULT).finditer(text)
