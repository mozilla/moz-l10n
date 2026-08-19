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

"""placeholder.unsupported -- the translation holds a placeholder that cannot be serialized."""

from __future__ import annotations

from moz.l10n.lint.model import Diagnostic, LintContext, Rule, SourceType, TargetType

from ...model import PatternMessage

NAME = "unsupported"
RULE = Rule(
    name=NAME,
    family="placeholder",
    default_severity="error",
)


def check(
    translation: TargetType, source: SourceType, context: LintContext
) -> list[Diagnostic]:
    return []


def webext_source(
    translation: PatternMessage, context: LintContext
) -> tuple[str, list[Diagnostic]]:
    """
    Rebuild the messages.json source text of `translation`, reporting any
    placeholder that has no original spelling to fall back on.

    Serializing through moz.l10n would escape `$` in literal content, which
    would hide exactly the placeholder typos this family is looking for, so
    each part contributes its recorded `source` attribute verbatim instead.
    A part without one cannot be written back to messages.json at all.
    """
    diagnostics: list[Diagnostic] = []
    source = ""
    for part in translation.pattern:
        if isinstance(part, str):
            source += part
            continue
        part_source = part.attributes.get("source", None)
        if isinstance(part_source, str):
            source += part_source

        diagnostics.append(
            RULE.diagnostic(
                f"Unsupported placeholder: {part}",
                severity=context.severity_of(RULE),
                key=context.key,
            )
        )
    return source, diagnostics
