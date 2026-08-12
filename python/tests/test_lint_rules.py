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
from importlib import import_module
from pathlib import Path

import moz.l10n.formats
import moz.l10n.lint
import pytest
from moz.l10n.lint.model import Diagnostic, Rule
from moz.l10n.lint.parse import source_error, translation_error
from pytest_snapshot.plugin import Snapshot


def _module_full_name(rule_family: str, rule_name: str) -> str:
    return (
        f"moz.l10n.lint.{rule_family.replace('-', '_')}.{rule_name.replace('-', '_')}"
    )


@pytest.mark.parametrize(
    "rule_family", moz.l10n.lint.FAMILIES, ids=lambda p: f"rule family: {p}"
)
def test_rule_meta(rule_family: str, subtests: pytest.Subtests):
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


@pytest.mark.parametrize("l10n_extension", moz.l10n.formats.l10n_extensions, ids=lambda p: f"type: {p}")
def test_parse_rules(l10n_extension: str, snapshot: Snapshot):
    common_dir = moz.l10n.lint.PARSE_COMMON / source_error.NAME
    source_test_file = common_dir / f"source{l10n_extension}"
    if not source_test_file.is_file():
        pytest.skip(f"No test file for {l10n_extension}")

    raw = source_test_file.read_text()
    resource_format = moz.l10n.formats.detect_format(source_test_file.name, raw)
    assert isinstance(resource_format, moz.l10n.formats.Format)
    context = moz.l10n.lint.LintContext(
        resource_format=resource_format,
        path=str(source_test_file),
    )
    _source, diagnostics = source_error.parse_check(raw, context)
    assert all(isinstance(d, Diagnostic) for d in diagnostics)

    diagnostics_json = json.dumps([asdict(d) for d in diagnostics], indent=2)

    snapshot.snapshot_dir = common_dir
    snapshot.assert_match(diagnostics_json, f"expected{l10n_extension}.json")


@pytest.mark.parametrize("rule_family", moz.l10n.lint.FAMILIES, ids=lambda p: f"rule family: {p}")
def test_rules(rule_family: str, subtests: pytest.Subtests):
    for rule_name in moz.l10n.lint.RULES[rule_family]:
        module_name = moz.l10n.lint.get_module_name(rule_family, rule_name)
        with subtests.test(module_name):
            module = moz.l10n.lint.get_rule_module(rule_family, rule_name)
            module

    # # Find all test functions in the module
    # test_functions = [
    #     getattr(module, attr_name)
    #     for attr_name in dir(module)
    #     if attr_name.startswith("test_") and callable(getattr(module, attr_name))
    # ]

    # # Run the discovered tests
    # for test_func in test_functions:
    #     test_func()


# @pytest.mark.parametrize("rule_dir", RULE_PATHS, ids=lambda p: f"{p.parent.name}/{p.name}")
# def test_python_rules(rule_dir: Path):
#     family = rule_dir.parent.name
#     rule_name = rule_dir.name
#     full_id = f"{family}/{rule_name}"

#     assert full_id in RULE_REGISTRY, f"No Python implementation registered for {full_id}"

#     # Load fixture and expected output
#     source_code = (rule_dir / "source.ftl").read_text()
#     expected_data = json.loads((rule_dir / "expected.json").read_text())

#     # Parse Fluent AST & Run Visitor Rule
#     ast = parse(source_code)
#     rule_instance = RULE_REGISTRY[full_id]()
#     rule_instance.visit(ast)

#     # Format actual results to match expected.json schema
#     actual_data = [
#         {
#             "rule_id": d.rule_id,
#             "line": d.line,
#             "column": d.column,
#             "message": d.message,
#             "severity": d.severity,
#         }
#         for d in rule_instance.diagnostics
#     ]

#     assert actual_data == expected_data

if __name__ == "__main__":
    pytest.main([__file__])
