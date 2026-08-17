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

Each rule is implemented in `moz/l10n/lint/<family>/<rule_name>.py` and is
documented in the matching `lint-rules/<family>/<rule-name>/` directory, which
is the shared source of truth for the Python and JS implementations.

`check()` runs every rule that applies to a single translation and its source.
"""

from __future__ import annotations

import typing
from importlib import import_module
from pathlib import Path

from moz.l10n.lint.model import (
    Diagnostic,
    LintContext,
    Rule,
    RuleModule,
    Severity,
    SourceType,
    TargetType,
)
from moz.l10n.lint.parse import source_error, translation_error

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
NAME_PATTERN = "{}.{}"
"""To string together family and rule name this is the recommended format."""

FAMILIES = tuple(
    i.name.replace("_", "-")
    for i in LINT_LIB.glob("*")
    if i.name != PARSE_FAMILY and i.is_dir() and i.name[0] not in "_."
)
"""Rule family names tuple.
All directories except "parse" in the Python lint directory. (with `-` for `_`)
"""

RULES: dict[str, list[str]] = {
    f: [
        r.stem.replace("_", "-")
        for r in (LINT_LIB / f).glob("*.py")
        if not r.name.startswith("_")
    ]
    for f in FAMILIES
}
"""Rule names dictionary `family: [rules]`.
From all Python files in the (non-parse) family dirs. (with `-` for `_`)
"""

PARSE_RULES: list[str] = [
    r.stem.replace("_", "-")
    for r in (LINT_LIB / PARSE_FAMILY).glob("*.py")
    if not r.name.startswith("_")
]
"""List of rules from the "parse" family.
These are special and return parsed data additionally to a diagnostics list.
"""

_RULE_MODULES: dict[str, RuleModule] = {}


def check(
    context: LintContext,
    raw_translation: str | None = None,
    raw_source: str | None = None,
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
    if context.raw_translation is None:
        if raw_translation is None:
            raise RuntimeError("We need raw translation data to check!")
        context.raw_translation = raw_translation

    if raw_source is not None:
        context.raw_source = raw_source

    diagnostics = []
    translation, source, parse_diagnostics = check_parse(context)
    diagnostics.extend(parse_diagnostics)
    if translation is None:
        return diagnostics

    diagnostics.extend(check_rules(translation, source, context))

    return diagnostics


def check_parse(
    context: LintContext,
) -> tuple[TargetType, SourceType, list[Diagnostic]]:
    """
    Perform `parse_check` on the contexts `raw_translation` and `raw_source`.
    Return 3 part tuple of parsed types and list of diagnostics.
    """
    diagnostics = []
    if context.raw_source:
        source, source_diagnostics = source_error.parse_check(context)
        diagnostics.extend(source_diagnostics)
    else:
        source = None

    translation, translation_diagnostics = translation_error.parse_check(context)
    if translation_diagnostics:
        diagnostics.extend(translation_diagnostics)
        translation = None

    return translation, source, diagnostics


def check_rules(
    translation: TargetType, source: SourceType, context: LintContext
) -> list[Diagnostic]:
    """
    Perform `check` of enabled rules on parsed `translation` and `source` resources.
    Return list of diagnostics.
    """
    diagnostics = []
    for rule_family, rules in RULES.items():
        for rule_name in rules:
            full_name = get_full_name(rule_family, rule_name)
            if context.enabled_rules and full_name not in context.enabled_rules:
                continue

            rule_module = get_rule_module(full_name)

            try:
                diagnostics.extend(rule_module.check(translation, source, context))
            except Exception as error:
                raise RuntimeError(
                    f'Error running rule "{rule_module.__name__}":\n'
                    f'  file: "{rule_module.__file__}"\n'
                    f'  translation: {translation}\n'
                    f'  source: {source}\n',
                    f'  context: {context}\n'
                    f'  error: {error}'
                )
    return diagnostics


def get_full_name(rule_family: str, rule_name: str) -> str:
    """Given rule family and rule name strings produce a module name string.
    Concatenating with a dot and replacing any `-` with `_`.
    """
    return NAME_PATTERN.format(rule_family, rule_name)


def get_rule_module(part_one: str, part_two: str | None = None) -> RuleModule:
    """Given `rule_family` and `rule_name` strings import according rule module."""
    if part_two is None:
        module_name = part_one
    else:
        module_name = get_full_name(part_one, part_two)

    module_name = module_name.replace('-', '_')
    if module_name in _RULE_MODULES:
        return _RULE_MODULES[module_name]

    module = typing.cast(RuleModule, import_module(f"{LINT_PACKAGE}.{module_name}"))
    _RULE_MODULES[module_name] = module

    return module
