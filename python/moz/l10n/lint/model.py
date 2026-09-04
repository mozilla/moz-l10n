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
from typing import Any, Iterator

from moz.l10n.formats import Format
from moz.l10n.model import Message


class Severity(str, Enum):
    """Linting rule severity that can be JSON serialized to `str`."""

    ERROR = "error"
    WARNING = "warning"


NAME_PATTERN = "{}.{}"
"""To string together family and rule name this is the recommended format."""


@dataclass
class Diagnostic:
    """A single rule violation."""

    rule_name: str
    """The rule's short descriptive name, e.g. `source-error`."""

    rule_family: str
    """The rule family name, e.g. `parse`."""

    message: str = ""
    """Human-readable description of the violation."""

    severity: Severity = Severity.ERROR
    """Resolved severity, which may differ from the rule's default."""


class Rule:
    """
    Foundational linting rule class.
    Carries a rules metadata and the dedicated `check` method yielding diagnostics.
    """

    name: str
    family: str
    full_name: str
    default_severity: Severity
    format_severities: dict[Format, Severity]

    def check(
        self,
        target: Message | None,
        source: Message | None,
        context: LintContext,
    ) -> Iterator[Diagnostic]:
        raise NotImplementedError

    def report(
        self, message: str = "", context: LintContext | None = None, **kwargs: Any
    ) -> Diagnostic:
        """Build a diagnostic with incoming message and context.
        `message` can be empty to enable overrides that build it from context or other inputs.
        Thus `context` needs to have a default as well otherwise we'd need to change the order.
        """
        if not message.strip():
            raise ValueError("Diagnostic message cannot be empty!")

        severity = kwargs.pop(
            "severity",
            context.severity_of(self) if context is not None else self.default_severity,
        )

        return Diagnostic(
            rule_name=self.name,
            rule_family=self.family,
            message=message,
            severity=severity,
            **kwargs,
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.full_name = NAME_PATTERN.format(self.family, self.name)

    def __str__(self) -> str:
        return self.full_name

    def __repr__(self) -> str:
        return f"Rule({self!r})"


@dataclass
class LintContext:
    """Everything a rule or a diagnostic needs to know about a resource being checked."""

    # local, per resource context:
    resource_format: Format
    """The `moz.l10n.formats.Format`."""

    severity: dict[str, Severity] = field(default_factory=dict)
    """Per-rule severity overrides, keyed by rule name."""

    def severity_of(self, rule: Rule, fallback: Severity | None = None) -> Severity:
        """The effective severity of `rule`, applying any override.
        Pass a `fallback` severity to be taken if overrides don't apply.
        So we don't need to change `default_severity`.
        """
        if rule.full_name in self.severity:
            return self.severity[rule.full_name]
        if (
            hasattr(rule, "format_severities")
            and self.resource_format in rule.format_severities
        ):
            return rule.format_severities[self.resource_format]

        return fallback or rule.default_severity


if __name__ == "__main__":
    pass
