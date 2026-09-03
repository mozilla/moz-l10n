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

from typing import Iterator

from moz.l10n.formats import Format
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.model import Message, PatternMessage


class Unsupported(Rule):
    name = "unsupported"
    family = "placeholder"
    default_severity = Severity.ERROR

    def check(
        self, target: Message | None, source: Message | None, context: LintContext
    ) -> Iterator[Diagnostic]:
        if context.resource_format is not Format.webext or not isinstance(
            target, PatternMessage
        ):
            return

        for part in target.pattern:
            if isinstance(part, str):
                continue

            part_source = part.attributes.get("source", None)
            if isinstance(part_source, str):
                continue

            yield self.diagnostic(
                f"Unsupported placeholder: {part}",
                severity=context.severity_of(self),
                id=context.id,
            )
