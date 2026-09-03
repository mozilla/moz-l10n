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

"""TBD:
Feedback from PR: https://github.com/mozilla/moz-l10n/pull/199#discussion_r3811700885
> Calling this same function from both here and the not-in-translation check is wasteful.
> It should be possible for the scan to be done once, and then two different errors generated from it."

Indeed that'd be really neat! But at the moment this would introduce quite some complexity!

Emitting arbitrary diagnostics is not the problem but:
* these diagnostics need to be build with different rule names and severities (also not impossible but wait ...)
* how to find a rule class for "not-in-reference"? Make `rule.name` empty, have a `rule.sub_rules` set? OK
* and now "not-in-reference" and "not-in-translation" point to the same class!?
  Keep track of what `rule.check` have been executed already to keep them from being executed twice?
* `rule.sub_severities` now! ...

OK let's keep the classes simple!
* cache on module level what messages have been scanned for placeholders!?
* When to flush the cache? Just let it grow?

This needs to be discussed further but for now calling `match_placeholders` twice seems like a pretty little price.
We're just getting started... Let's see what else comes up :D

OK New idea: these rules will most definitely be called in succession!
So we don't need to keep arbitrary instances or matches! The VERY LAST ONE will do!
Now `match_placeholders` tries to get from last match first only then orders a new one, puts it back to cache.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.lint.tools import (
    get_patterns,
    get_simple_preview,
    iter_placeholders,
    preview_placeholder,
)
from moz.l10n.model import Expression, Message


class NotInSource(Rule):
    name = "not-in-reference"
    family = "placeholder"
    default_severity = Severity.ERROR

    def check(
        self, target: Message | None, source: Message | None, context: LintContext
    ) -> Iterator[Diagnostic]:
        """
        Report both:
        * placeholders the translation uses that its source does not
        * every source placeholder the translation leaves out.
        """
        if target is None or source is None or context.resource_format is Format.fluent:
            return

        match = match_placeholders(target, source, context.resource_format)
        for placeholder in match.extra:
            yield self.diagnostic(
                message=f"{kind_of(placeholder)} {placeholder} not found in reference",
                severity=context.severity_of(self),
            )


class NotInTarget(Rule):
    name = "not-in-translation"
    family = "placeholder"
    default_severity = Severity.WARNING

    def check(
        self, target: Message | None, source: Message | None, context: LintContext
    ) -> Iterator[Diagnostic]:
        """ """
        if target is None or source is None:
            return

        match = match_placeholders(target, source, context.resource_format)
        for placeholder in match.missing:
            yield self.diagnostic(
                f"{kind_of(placeholder)} {placeholder} not found in translation",
                severity=context.severity_of(self),
            )


ignored_placeholders = {"%%", "%n"}
"""printf escapes that carry no argument, so need no counterpart in the source."""


@dataclass(frozen=True)
class PlaceholderMatch:
    """The outcome of comparing a translation's placeholders against its source."""

    extra: list[str] = field(default_factory=list)
    """Placeholders used by the translation that the source does not declare."""

    missing: list[str] = field(default_factory=list)
    """Placeholders declared by the source that the translation does not use."""


def kind_of(placeholder: str) -> str:
    """`"Element"` for markup, `"Placeholder"` for everything else."""
    return "Element" if placeholder.startswith("<") else "Placeholder"


def match_placeholders(
    target: Message, source: Message, resource_format: Format
) -> PlaceholderMatch:
    """
    Compare placeholders of `translation` against `source` ones.

    Both sides are flattened back to their format-native spelling first, so a
    placeholder typed out literally by the translator matches a source
    placeholder carrying the same `@source` attribute.
    """
    if cached := _PatternCache.get(target, source):
        return cached

    source_placeholders = _source_placeholders(source)
    if source_placeholders is None:
        return _PatternCache.set(target, source, _PatternCache.no_match)

    extra: list[str] = []
    found: set[str] = set()
    for pattern in get_patterns(target):
        preview = get_simple_preview(pattern)
        for match in iter_placeholders(preview, resource_format):
            for placeholder in source_placeholders:
                if preview.startswith(placeholder, match.start()):
                    found.add(placeholder)
                    break
            else:
                if match[0] not in ignored_placeholders:
                    extra.append(match[0])

    return _PatternCache.set(
        target,
        source,
        PlaceholderMatch(extra=extra, missing=sorted(source_placeholders - found)),
    )


def _source_placeholders(source: Message) -> set[str] | None:
    """
    The format-native spelling of every placeholder in `source`.

    Returns `None` when the source contains a bare `%` in its text: the
    message is then presumably not printf-formatted, and scanning it for
    printf specifiers would only produce noise.
    """
    placeholders: set[str] = set()
    if source is None:
        return placeholders
    for pattern in get_patterns(source):
        for el in pattern:
            if isinstance(el, str):
                if "%" in el:
                    return None
            elif isinstance(el, Expression):
                placeholders.add(preview_placeholder(el))

    return placeholders


class _PatternCache:
    """Holds match for 1 set of given messages.
    To keep us from re-scanning the same messages on the very next check.
    """

    last_target: Message | None = None
    last_source: Message | None = None
    last_match: PlaceholderMatch = PlaceholderMatch()
    no_match: PlaceholderMatch = last_match

    @classmethod
    def get(
        cls, target: Message | None, source: Message | None
    ) -> PlaceholderMatch | None:
        if cls.last_target is target and cls.last_source is source:
            return cls.last_match
        return None

    @classmethod
    def set(
        cls,
        last_target: Message | None,
        last_source: Message | None,
        last_match: PlaceholderMatch,
    ) -> PlaceholderMatch:
        cls.last_target = last_target
        cls.last_source = last_source
        cls.last_match = last_match
        return last_match
