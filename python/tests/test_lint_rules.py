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

import json
import typing
from dataclasses import asdict
from pathlib import Path

import moz.l10n.formats
import moz.l10n.lint
import moz.l10n.lint.testing
import pytest
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, Severity
from moz.l10n.lint.parse import SourceMessageError, TargetMessageError
from pytest_snapshot.plugin import Snapshot

# We're only parsing Message atm! No full resources yet!
PARSE_RULES = (
    pytest.param(
        SourceMessageError,
        "source",
        Severity.WARNING,
        id=f"rule: {SourceMessageError.name}",
    ),
    pytest.param(
        TargetMessageError,
        "example",
        Severity.ERROR,
        id=f"rule: {TargetMessageError.name}",
    ),
)
RULE_PAIRS = tuple((f, r) for f, rules in moz.l10n.lint.RULES.items() for r in rules)
RULES_NAMES = tuple(moz.l10n.lint.get_full_name(fam, r) for fam, r in RULE_PAIRS)


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

            rule_class = moz.l10n.lint.get_rule_class(rule_family, rule_name)
            assert isinstance(rule_class, type)
            assert issubclass(rule_class, Rule)
            assert isinstance(name, str)
            rule = rule_class()
            assert rule.name == rule_name

            check_func = getattr(rule, "check", None)
            if check_func is None:
                if rule_path := rule.get_path():
                    rule_path = (
                        f" {Path(rule_path).relative_to(moz.l10n.lint.LIB_ROOT)}"
                    )
                assert False, (
                    f'No "check" method on "{full_name}" rule class!{rule_path}'
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


@pytest.mark.parametrize("rule_class, fixture_stem, expect_severity", PARSE_RULES)
@pytest.mark.parametrize(
    "l10n_extension", moz.l10n.formats.l10n_extensions, ids=lambda p: f"type: {p}"
)
def test_parse_rules(
    rule_class, fixture_stem, expect_severity, l10n_extension: str, snapshot: Snapshot
):
    common_dir = moz.l10n.lint.PARSE_COMMON / rule_class.name
    test_file = common_dir / f"{fixture_stem}{l10n_extension}"
    if not test_file.is_file():
        pytest.skip(f"No test file for {test_file.name} for {rule_class.name}")
    is_source = fixture_stem == "source"
    snapshot_name = f"expected{l10n_extension}.json"
    if not (common_dir / snapshot_name).is_file():
        pytest.skip(f"No snapshot file for {test_file.name} for {rule_class.name}")

    raw = test_file.read_text()
    raw_src, raw_trg = (raw, None) if is_source else (None, raw)
    resource_format = moz.l10n.lint.testing.get_format(test_file, raw)
    assert resource_format is not None
    assert isinstance(resource_format, moz.l10n.formats.Format)
    context = LintContext(resource_format=resource_format, path=str(test_file))

    rule = rule_class()
    parsed, diagnostic = rule.parse_check(raw_src if is_source else raw_trg, context)
    assert isinstance(diagnostic, Diagnostic)
    assert diagnostic.rule_name == rule_class.name
    assert diagnostic.severity == expect_severity
    if diagnostic and not is_source:
        assert parsed is None

    snapshot.snapshot_dir = common_dir
    snapshot.assert_match(json.dumps([asdict(diagnostic)], indent=2), snapshot_name)


@pytest.mark.parametrize(("rule_family", "rule_name"), RULE_PAIRS, ids=RULES_NAMES)
def test_rule(rule_family: str, rule_name: str, snapshot: Snapshot, subtests):
    rule = moz.l10n.lint.get_rule_class(rule_family, rule_name)()
    rule_common = moz.l10n.lint.RULES_COMMON / rule.family / rule.name
    if not rule_common.is_dir():
        raise RuntimeError(f'No such lint-rule directory: "{rule_common}"!')

    for target, source, test_file, this_format in moz.l10n.lint.testing.iter_test_files(
        rule_common
    ):
        with subtests.test(
            f"{rule.get_full_name()}::{test_file.suffix}", ext=test_file.suffix
        ):
            snapshot_name = f"expected{test_file.suffix}.json"
            if not (rule_common / snapshot_name).is_file():
                pytest.skip(
                    f"No snapshot file for {test_file.name} for {rule.full_name}"
                )

            context = LintContext(resource_format=this_format, path=str(test_file))
            diagnostics = list(rule.check(target, source, context))

            snapshot.snapshot_dir = rule_common
            snapshot.assert_match(
                json.dumps([asdict(d) for d in diagnostics], indent=2), snapshot_name
            )


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
