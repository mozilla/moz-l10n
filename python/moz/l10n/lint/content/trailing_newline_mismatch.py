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

"""content.trailing-newline-mismatch - Source and translation must agree on a trailing newlines."""

from __future__ import annotations

from moz.l10n.lint.model import Diagnostic, LintContext, Rule, SourceType, TargetType
from moz.l10n.model import PatternMessage

NAME = "trailing-newline-mismatch"
RULE = Rule(name=NAME, family="content", default_severity="error")

MESSAGE = "Ending newline mismatch"


def check(
    translation: TargetType, source: SourceType, context: LintContext
) -> list[Diagnostic]:
    """Report translation that adds or drops the sources trailing newline."""
    if source is None or translation is None:
        return []

    source_str = _get_str(source, context.raw_source)
    target_str = _get_str(translation, context.raw_translation)
    if _count_trailing_newlines(source_str) == _count_trailing_newlines(target_str):
        return []

    return [
        RULE.diagnostic(
            MESSAGE,
            severity=context.severity_of(RULE),
            key=context.key,
            line=target_str.count("\n") + 1,
        )
    ]


def fix(source: str, translation: str) -> str:
    """
    Match translations trailing newline to source.
    """
    source_newlines = _count_trailing_newlines(source)
    if source_newlines == _count_trailing_newlines(translation):
        return translation

    new_line = "\n"
    return f"{translation.rstrip(new_line)}{new_line * source_newlines}"


def _get_str(s: str | SourceType, raw: str | None) -> str:
    check_string = (
        (s.pattern[-1] if s.pattern else "") if isinstance(s, PatternMessage) else s
    )
    if not isinstance(check_string, str):
        if raw is None:
            raise NotImplementedError(
                f'TODO: Implement this for format "{type(check_string)}"'
            )
        return raw
    return check_string


def _count_trailing_newlines(s: str) -> int:
    count = 0
    for char in reversed(s):
        if char != "\n":
            break
        count += 1
    return count
