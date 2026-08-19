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

"""Shared placeholder matching for the `placeholder` rule family."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from moz.l10n.lint._preview import get_patterns, get_simple_preview, preview_placeholder
from moz.l10n.model import Expression, Message

# re patterns
_MARKUP = r"<[^>]+>"
_PRINTF = r"%(?:[1-9]\$)?[-#+ 0,(]?[0-9.]*(?:hh?|ll?|[qztjLT])?.?"
_ANDROID_PLURAL = r"%#@\w+@"
_WEBEXT = r"\$[a-zA-Z0-9_]+\$?"

_RE_MAP: dict[str, re.Pattern[str]] = {
    "android": re.compile(f"{_MARKUP}|{_ANDROID_PLURAL}|{_PRINTF}"),
    "gettext": re.compile(f"{_MARKUP}|{_PRINTF}"),
    "xcode": re.compile(f"{_MARKUP}|{_PRINTF}"),
    "webext": re.compile(f"{_MARKUP}|{_WEBEXT}"),
}

# Fallback for generic/unknown formats
_RE_DEFAULT = re.compile(f"{_MARKUP}|{_PRINTF}|{_WEBEXT}")
"""Match all HTML/XML elements and Android & Xcode printf specifiers."""

ignored_placeholders = {"%%", "%n"}
"""printf escapes that carry no argument, so need no counterpart in the source."""


@dataclass
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
    translation: Message, source: Message, format_name: str
) -> PlaceholderMatch:
    """
    Compare placeholders of `translation` against `source` ones.

    Both sides are flattened back to their format-native spelling first, so a
    placeholder typed out literally by the translator matches a source
    placeholder carrying the same `@source` attribute.
    """
    source_placeholders = _source_placeholders(source)
    if source_placeholders is None:
        return PlaceholderMatch()

    extra: list[str] = []
    found: set[str] = set()
    for pattern in get_patterns(translation):
        preview = get_simple_preview(pattern)
        for match in _RE_MAP.get(format_name, _RE_DEFAULT).finditer(preview):
            rest = preview[match.start() :]
            for placeholder in source_placeholders:
                if rest.startswith(placeholder):
                    found.add(placeholder)
                    break
            else:
                if match[0] not in ignored_placeholders:
                    extra.append(match[0])

    missing = sorted(source_placeholders - found)
    return PlaceholderMatch(extra=extra, missing=missing)


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
