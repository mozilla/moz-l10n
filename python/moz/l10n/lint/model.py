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

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator

from moz.l10n.formats import Format
from moz.l10n.model import Id, Message

Severity = Enum("Severity", ("ERROR", "WARNING"))


@dataclass
class Diagnostic:
    """A single rule violation."""

    rule_name: str
    """The rule's short descriptive name, e.g. `parse-error`."""

    message: str = ""
    """Human-readable description of the violation."""

    severity: Severity = Severity.ERROR
    """Resolved severity, which may differ from the rule's default."""

    message_id: Id | None = None
    """The message id the diagnostic points at, if the format has one."""

    line: int | None = None
    """1-based line within the checked string."""

    column: int | None = None
    """1-based column within the checked string."""


class Rule:
    """
    Implementation-side metadata for a lint rule.

    Mirrors the `rule.toml` of the matching `lint-rules/<family>/<name>/`
    directory, which is the shared source of truth across implementations.
    """

    name: str
    family: str
    default_severity: Severity
    format_severities: dict[Format, Severity]

    def check(
        self,
        target: Message | None,
        source: Message | None,
        context: LintContext,
    ) -> Iterator[Diagnostic]:
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.family}::{self.name}"

    def diagnostic(
        self,
        message: str,
        *,
        severity: Severity | None = None,
        message_id: Id | None = None,
        line: int | None = None,
        column: int | None = None,
    ) -> Diagnostic:
        return Diagnostic(
            rule_name=self.name,
            message=message,
            severity=severity or self.default_severity,
            message_id=message_id,
            line=line,
            column=column,
        )


@dataclass
class LintContext:
    """
    Everything a rule or eventually a diagnostic needs to know about a resource being checked.
    * `resource_format` - A `moz.l10n.formats.Format`, or its name as a string.
    * `raw_source` - The original unparsed source string.
    * `raw_translation` - The original unparsed translation string.
    * `path` - Path to the resource being checked, if known.
    * `key` - The message id/key of the resource being checked, if known.
    * `severity` - Per-rule severity overrides, keyed by rule name.
    * `enabled_rules` - Collection of enabled rules where `None` means ALL rules.
    * `allows_empty_translations` - If set, an empty translation is reported as a warning rather than an error.
    """

    # local, per resource context:
    resource_format: Format
    """The `moz.l10n.formats.Format`."""

    id: Id | None = None
    """The message id/key of the resource being checked, if known."""

    severity: dict[str, Severity] = field(default_factory=dict)
    """Per-rule severity overrides, keyed by rule name."""

    raw_source: str | None = None
    """Unparsed source string."""

    raw_translation: str | None = None
    """Unparsed translation string."""

    path: str | None = None
    """Path to the resource being checked, if known."""

    # global context:
    enabled_rules: set[str] | None = None
    """Collection of enabled rules where `None` means ALL rules."""

    def severity_of(self, rule: Rule) -> Severity:
        """The effective severity of `rule`, applying any override."""
        if rule.name in self.severity:
            return self.severity[rule.name]
        if self.resource_format in rule.format_severities:
            return rule.format_severities[self.resource_format]
        return rule.default_severity


def get_line_col(text: str | None, offset: int) -> tuple[int, int]:
    """Calculate 1-based line and column of a character `offset` or position in `text`."""
    if not text or offset <= 0:
        return 1, 1
    head = text[:offset]
    line = head.count("\n") + 1
    return line, offset - (head.rfind("\n") + 1) + 1


if __name__ == "__main__":
    pass
