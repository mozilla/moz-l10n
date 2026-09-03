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

import sys
from dataclasses import dataclass, field
from enum import Enum
from types import ModuleType
from typing import Any, Iterator

from moz.l10n.formats import Format
from moz.l10n.model import Id, Message


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

    id: Id | None = None
    """The resource id or "key" the diagnostic points at, if there is one."""

    line: int | None = None
    """1-based line within the checked string."""

    column: int | None = None
    """1-based column within the checked string."""


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

    def diagnostic(
        self,
        message: str,
        *,
        severity: Severity | None = None,
        id: Id | None = None,
        line: int | None = None,
        column: int | None = None,
    ) -> Diagnostic:
        """Build a diagnostic with incoming message, violation details plus what the rule itself knows."""
        return Diagnostic(
            rule_name=self.name,
            rule_family=self.family,
            message=message,
            severity=severity or self.default_severity,
            id=id,
            line=line,
            column=column,
        )

    def get_module(self) -> ModuleType | None:
        """Get the rule's module object."""
        return sys.modules.get(self.__class__.__module__)

    def get_path(self) -> str:
        """Get the string path to where to the rule implementation."""
        module = self.get_module()
        if module is None or module.__file__ is None:
            return ""
        return module.__file__

    @classmethod
    def get_full_name(cls) -> str:
        """Build rule full_name family+rule-name.
        Works when not yet instantiated. Use `.full_name` otherwise.
        """
        return NAME_PATTERN.format(cls.family, cls.name)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.full_name = NAME_PATTERN.format(self.family, self.name)

    def __str__(self) -> str:
        return self.full_name

    def __repr__(self) -> str:
        return f"Rule({self!r})"


@dataclass
class LintContext:
    """
    Everything a rule or eventually a diagnostic needs to know about a resource being checked.
    * `resource_format` - A `moz.l10n.formats.Format`, or its name as a string.
    * `id` - The message id of the resource being checked, if known.
    * `severity` - Per-rule severity overrides, keyed by rule name.
    * `path` - Path to the resource being checked, if known.
    * `enabled_rules` - Collection of enabled rules where `None` means ALL rules.
    """

    # local, per resource context:
    resource_format: Format
    """The `moz.l10n.formats.Format`."""

    id: Id | None = None
    """The resource id/key of the entry being checked, if known."""

    severity: dict[str, Severity] = field(default_factory=dict)
    """Per-rule severity overrides, keyed by rule name."""

    path: str | None = None
    """Path to the resource being checked, if known."""

    # global context:
    enabled_rules: set[str] | None = None
    """Collection of enabled rules where `None` means ALL rules."""

    target_locale: str | None = None
    """Source locale BCP-47 language code (e.g., "de", "en-US")."""

    source_locale: str | None = None
    """Source locale BCP-47 language code (e.g., "de", "en-US")."""

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
