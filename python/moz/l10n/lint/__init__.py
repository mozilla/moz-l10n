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

"""
Lint rules for localizable content.

Each rule is implemented in `moz/l10n/lint/<family>/<family_module>.py::RuleName` and is
documented in the matching `lint-rules/<family>/<rule-name>/` directory, which
is the shared source of truth for the Python and JS implementations.

`check()` runs every rule that applies to a single target and its source.
"""

from __future__ import annotations

import inspect
import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Iterator

from moz.l10n.lint.model import NAME_PATTERN, Diagnostic, LintContext, Rule, Severity
from moz.l10n.lint.parse import SourceMessageError, TargetMessageError
from moz.l10n.model import Message

__all__ = ["Diagnostic", "LintContext", "Rule", "Severity", "check"]

LINT_LIB = Path(__file__).parent
LIB_ROOT = LINT_LIB.parent
PY_ROOT = LIB_ROOT.parent.parent
ROOT = PY_ROOT.parent
RULES_COMMON = ROOT / "lint-rules"

DOCS_NAME = "docs.md"
RULE_CONFIG_NAME = "rule.toml"
LINT_PACKAGE = "moz.l10n.lint"
PARSE_FAMILY = "parse"
PARSE_COMMON = RULES_COMMON / PARSE_FAMILY

FAMILIES = tuple(
    i.name.replace("_", "-")
    for i in LINT_LIB.glob("*")
    if i.name != PARSE_FAMILY and i.is_dir() and i.name[0] not in "_."
)
"""Rule family names tuple.
All directories except "parse" in the Python lint directory. (with `-` for `_`)
"""

RULES: dict[str, tuple[str, ...]] = {
    f: tuple(
        rd.name for rd in (RULES_COMMON / f).glob("*") if (rd / DOCS_NAME).is_file()
    )
    for f in FAMILIES
}
"""Rule names dictionary `family: [rules]`.
From all folders with a `docs.md` in common family dirs. (with `-` for `_`).
"""

PARSE_RULES: tuple[str, ...] = tuple(
    pd.name for pd in PARSE_COMMON.glob("*") if (pd / DOCS_NAME).is_file()
)
"""List of rules from the "parse" family.
These are special and return parsed data additionally to a diagnostics list.
"""

_RULE_MODULES: dict[str, list[ModuleType]] = {}
"""Rule family modules cache."""


def check(
    raw_target: str,
    raw_source: str | None,
    context: LintContext,
) -> list[Diagnostic]:
    """
    Check a translation against its source.

    Ingest "raw" strings, hand them to their parser according to context.
    Iterate over applying rules with parsed data and collect diagnostics.

    Both strings are in the syntax that `context.resource_format` uses for a
    single message, which for everything but Fluent means MF2.

    Diagnostics come back in the order the rules ran, each carrying its own
    resolved severity.
    """
    diagnostics = []
    target, source, parse_diagnostics = check_parse(raw_target, raw_source, context)
    diagnostics.extend(parse_diagnostics)
    if any(d.severity is Severity.ERROR for d in diagnostics):
        return diagnostics

    diagnostics.extend(check_rules(target, source, context))

    return diagnostics


def check_parse(
    raw_target: str | None, raw_source: str | None, context: LintContext
) -> tuple[Message | None, Message | None, list[Diagnostic]]:
    """
    Perform `parse_check` on `raw_target` and `raw_source`.
    Return 3 part tuple of parsed types and list of diagnostics.
    """
    diagnostics = []
    if raw_source:
        source, source_diagnostics = SourceMessageError().parse_check(
            raw_source, context
        )
        if source_diagnostics:
            diagnostics.append(source_diagnostics)
    else:
        source = None

    target, target_diagnostics = TargetMessageError().parse_check(raw_target, context)
    if target_diagnostics:
        diagnostics.append(target_diagnostics)
        target = None

    return target, source, diagnostics


def check_rules(
    target: Message | None, source: Message | None, context: LintContext
) -> list[Diagnostic]:
    """
    Perform `check` of enabled rules on parsed `target` and `source` resources.
    Return list of diagnostics.
    """
    diagnostics = []
    for rule_family, rules in RULES.items():
        for rule_name in rules:
            full_name = get_full_name(rule_family, rule_name)
            if context.enabled_rules and full_name not in context.enabled_rules:
                continue

            rule = get_rule_class(rule_family, rule_name)()

            try:
                diagnostics.extend(rule.check(target, source, context))
            except Exception as error:
                raise RuntimeError(
                    f'Error running rule "{rule.full_name}":\n'
                    f'  file: "{sys.modules[rule.__module__].__file__}"\n'
                    f"  target: {target}\n"
                    f"  source: {source}\n",
                    f"  context: {context}\n  error: {error}",
                )
    return diagnostics


def get_full_name(rule_family: str, rule_name: str) -> str:
    """Given rule family and rule name strings produce a rule name string.
    Concatenating with a dot band replacing any `-` with `_`.
    """
    return NAME_PATTERN.format(rule_family, rule_name)


def get_rule_class(rule_family: str, rule_name: str) -> type[Rule]:
    """Given `rule_family` and `rule_name` strings import according rule module, pass rule class."""
    if rule_family in _RULE_MODULES:
        family_modules = _RULE_MODULES[rule_family]
    else:
        family_mod_names = [
            i.stem
            for i in (LINT_LIB / rule_family).glob("*.py")
            if i.is_file() and i.name != "__init__.py"
        ]
        family_modules = [
            import_module(f"{LINT_PACKAGE}.{rule_family}.{module_name}")
            for module_name in family_mod_names
        ]
        _RULE_MODULES[rule_family] = family_modules

    for rule_module in family_modules:
        for rule_class in iter_rule_classes(rule_module):
            if rule_class.name == rule_name:
                return rule_class

    raise RuntimeError(f'Could not find Rule class for name "{rule_name}"!')


def iter_rule_classes(rule_module: ModuleType) -> Iterator[type[Rule]]:
    """Iterate over found `Rule` subclasses."""
    for _, object in inspect.getmembers(rule_module):
        if not isinstance(object, type):
            continue
        if not issubclass(object, Rule) or not hasattr(object, 'name'):
            continue
        if object is Rule:
            continue
        yield object


if __name__ == "__main__":
    get_rule_class("content", "empty-translation")
