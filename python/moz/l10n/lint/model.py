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
from typing import Callable, Literal, Protocol
from xmlrpc.client import boolean

from fluent.syntax import ast as ftl
from moz.l10n.formats import Format
from moz.l10n.model import Message

Severity = Literal["error", "warning", "info"]


class SEVERITY:
    error: Severity = "error"
    warning: Severity = "warning"
    info: Severity = "info"


"""How a rule violation is reported."""


TargetType = Message | ftl.EntryType | None
SourceType = Message | ftl.EntryType | None


class RuleModule(Protocol):
    """Dedicated rule validation module. Must have a `check` function."""

    check: Callable[[TargetType, SourceType, LintContext], list[Diagnostic]]
    NAME: str
    RULE: Rule
    __file__: str
    __name__: str


@dataclass
class Diagnostic:
    """A single rule violation."""

    # rule_id: str
    # """The rule's stable numeric identifier, e.g. `"M001"`. May be empty."""

    rule_name: str
    """The rule's short descriptive name, e.g. `parse-error`."""

    message: str = ""
    """Human-readable description of the violation."""

    severity: Severity = "error"
    """Resolved severity, which may differ from the rule's default."""

    key: str | None = None
    """The message id/key the diagnostic points at, if the format has one."""

    line: int = 1
    """1-based line within the checked string."""

    column: int = 1
    """1-based column within the checked string."""


@dataclass(frozen=True)
class Rule:
    """
    Implementation-side metadata for a lint rule.

    Mirrors the `rule.toml` of the matching `lint-rules/<family>/<name>/`
    directory, which is the shared source of truth across implementations.
    """

    name: str
    family: str
    default_severity: Severity

    def __str__(self) -> str:
        return f"{self.family}::{self.name}"

    def diagnostic(
        self,
        message: str,
        *,
        severity: Severity | None = None,
        key: str | None = None,
        line: int = 1,
        column: int = 1,
    ) -> Diagnostic:
        return Diagnostic(
            # rule_id=self.id,
            rule_name=self.name,
            message=message,
            severity=severity or self.default_severity,
            key=key,
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
    resource_format: Format | str
    """
    A `moz.l10n.formats.Format`, or its name as a string.

    Values not matching a known format are accepted, so that formats which
    moz.l10n does not parse itself (such as Pontoon's `xcode`) may be used.
    """

    raw_source: str | None = None
    """Unparsed source string."""

    raw_translation: str | None = None
    """Unparsed translation string."""

    path: str | None = None
    """Path to the resource being checked, if known."""

    key: str | None = None
    """The message id/key of the resource being checked, if known."""

    severity: dict[str, Severity] = field(default_factory=dict)
    """Per-rule severity overrides, keyed by rule name."""

    is_fluent: boolean = False
    """Simple boolean. Is this Fluent True/False."""

    format_name: str = ""
    """The resource format as a lower-case string."""

    # global context:
    enabled_rules: set[str] | None = None
    """Collection of enabled rules where `None` means ALL rules."""

    allows_empty_translations: bool = False
    """If set, an empty translation is reported as a warning rather than an error."""

    def severity_of(self, rule: Rule) -> Severity:
        """The effective severity of `rule`, applying any override."""
        return self.severity.get(rule.name, rule.default_severity)

    def __post_init__(self):
        if isinstance(self.resource_format, Format):
            self.format_name = self.resource_format.name
            self.is_fluent = self.resource_format == Format.fluent
        else:
            # Unwrap Pontoon's `Resource.Format` TextChoices str enum.
            self.format_name = str(
                getattr(self.resource_format, "value", self.resource_format)
            ).lower()
            self.is_fluent = self.format_name == Format.fluent.name.lower()


def get_line_col(text: str | None, offset: int) -> tuple[int, int]:
    """Calculate 1-based line and column of a character `offset` or position in `text`."""
    if not text or offset <= 0:
        return 1, 1
    head = text[:offset]
    line = head.count("\n") + 1
    return line, offset - (head.rfind("\n") + 1) + 1


if __name__ == "__main__":
    pass
