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

import json
import typing
from dataclasses import asdict
from pathlib import Path

import moz.l10n.formats
import moz.l10n.lint
import pytest
from moz.l10n.lint.model import Diagnostic, Rule, Severity
from moz.l10n.lint.parse import source_error, translation_error
from pytest_snapshot.plugin import Snapshot

PARSE_RULES = (
    pytest.param(
        source_error,
        "source",
        Severity.WARNING,
        id=f"rule: {source_error.NAME}",
    ),
    pytest.param(
        translation_error,
        "example",
        Severity.ERROR,
        id=f"rule: {translation_error.NAME}",
    ),
)


@pytest.mark.parametrize(
    "rule_family", moz.l10n.lint.FAMILIES, ids=lambda p: f"rule family: {p}"
)
def test_rule_meta(rule_family: str, subtests):
    family_common_dir: Path = moz.l10n.lint.RULES_COMMON / rule_family
    assert family_common_dir.is_dir(), f'No such rule family in common "{rule_family}"!'

    for rule_name in moz.l10n.lint.RULES[rule_family]:
        full_name = f"{rule_family}/{rule_name}"
        rule_common_dir: Path = family_common_dir / rule_name
        with subtests.test(f"test_{full_name}", rule_name=rule_name):
            assert rule_common_dir.is_dir(), (
                f'No such rule dir in common "{full_name}"!'
            )

            for name in moz.l10n.lint.DOCS_NAME, moz.l10n.lint.RULE_CONFIG_NAME:
                path = rule_common_dir / name
                assert path.is_file(), f'"{full_name}" has no "{name}" file!'

            module = moz.l10n.lint.get_rule_module(rule_family, rule_name)
            assert module.__file__ is not None

            name = getattr(module, "NAME", None)
            assert name is not None, (
                f'No "NAME" in "{full_name}" rule module!\n'
                f" {Path(module.__file__).relative_to(moz.l10n.lint.ROOT)}"
            )
            assert isinstance(name, str)
            assert name == rule_name

            rule = getattr(module, "RULE", None)
            assert rule is not None, (
                f'No "RULE" in "{full_name}" rule module!\n'
                f" {Path(module.__file__).relative_to(moz.l10n.lint.ROOT)}"
            )
            assert isinstance(rule, Rule)
            assert rule.name == rule_name

            check_func = getattr(module, "check", None)
            assert check_func is not None, (
                f'No "check" function in "{full_name}" rule module!\n'
                f" {Path(module.__file__).relative_to(moz.l10n.lint.ROOT)}"
            )
            assert isinstance(check_func, typing.Callable)

    for common_dir in moz.l10n.lint.RULES_COMMON.glob("*"):
        if (
            not common_dir.is_dir()
            or common_dir.name.startswith("_")
            or common_dir.name == moz.l10n.lint.PARSE_FAMILY
        ):
            continue

        assert common_dir.name in moz.l10n.lint.FAMILIES, (
            f'Common rule family "{common_dir.name}" is not in implementation directory!'
        )
        for common_rule_dir in common_dir.glob("*"):
            if not common_rule_dir.is_dir() or common_rule_dir.name.startswith("_"):
                continue
            assert common_rule_dir.name in moz.l10n.lint.RULES[common_dir.name], (
                f'Rule "{common_rule_dir.name}" is not implemented!'
            )


@pytest.mark.parametrize("rule_module, fixture_stem, expect_severity", PARSE_RULES)
@pytest.mark.parametrize(
    "l10n_extension", moz.l10n.formats.l10n_extensions, ids=lambda p: f"type: {p}"
)
def test_parse_rules(
    rule_module, fixture_stem, expect_severity, l10n_extension: str, snapshot: Snapshot
):
    common_dir = moz.l10n.lint.PARSE_COMMON / rule_module.NAME
    test_file = common_dir / f"{fixture_stem}{l10n_extension}"
    if not test_file.is_file():
        pytest.skip(f"No test file for {test_file.name} for {rule_module.NAME}")

    raw = test_file.read_text()
    raw_src, raw_trg = (raw, None) if fixture_stem == "source" else (None, raw)
    resource_format = moz.l10n.formats.detect_format(test_file.name, raw)
    assert resource_format is not None
    assert isinstance(resource_format, moz.l10n.formats.Format)
    context = moz.l10n.lint.LintContext(
        resource_format=resource_format,
        path=str(test_file),
        raw_source=raw_src,
        raw_translation=raw_trg,
    )

    parsed, diagnostics = rule_module.parse_check(context)
    assert all(isinstance(d, Diagnostic) for d in diagnostics)
    assert all(d.rule_name == rule_module.NAME for d in diagnostics)
    assert all(d.severity == expect_severity for d in diagnostics)
    if diagnostics and rule_module is translation_error:
        assert parsed is None

    snapshot.snapshot_dir = common_dir
    snapshot.assert_match(
        json.dumps([asdict(d) for d in diagnostics], indent=2),
        f"expected{l10n_extension}.json",
    )


@pytest.mark.parametrize(
    "rule_family", moz.l10n.lint.FAMILIES, ids=lambda p: f"rule family: {p}"
)
def test_rules(rule_family: str, subtests):
    for rule_name in moz.l10n.lint.RULES[rule_family]:
        module_name = moz.l10n.lint.get_full_name(rule_family, rule_name)
        with subtests.test(module_name):
            module = moz.l10n.lint.get_rule_module(rule_family, rule_name)
            module


if __name__ == "__main__":
    pytest.main([__file__])
