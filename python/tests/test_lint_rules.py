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
from dataclasses import asdict

import moz.l10n.formats
import moz.l10n.lint
import pytest
from moz.l10n.lint.model import SEVERITY, Diagnostic
from moz.l10n.lint.parse import source_error, translation_error
from pytest_snapshot.plugin import Snapshot

PARSE_RULES = (
    pytest.param(
        source_error,
        "source",
        SEVERITY.warning,
        id=f"rule: {source_error.NAME}",
    ),
    pytest.param(
        translation_error,
        "example",
        SEVERITY.error,
        id=f"rule: {translation_error.NAME}",
    ),
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
def test_rules(rule_family: str, subtests: pytest.Subtests):
    for rule_name in moz.l10n.lint.RULES[rule_family]:
        module_name = moz.l10n.lint.get_full_name(rule_family, rule_name)
        with subtests.test(module_name):
            module = moz.l10n.lint.get_rule_module(rule_family, rule_name)
            module


if __name__ == "__main__":
    pytest.main([__file__])
