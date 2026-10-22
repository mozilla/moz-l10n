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

"""Testing our linting rules we're aiming to improve our strategies

Let's have test data files in common lint-rules directory:
  * each rule has it's own files
  * same data for all implementations, identical coverage
  * snapshot files to test against
  * reduces "code in code"
  * easy to expand test cases without writing new test code

Each test case has 3 files. For instance:
  * test_X.message.ftl.target
  * test_X.message.ftl.source
  * test_X.message.ftl.expected

As in `lint-rules/{family}/{rule}/test{suffix}.{model}.{format_ext}.{type}`. Where:
  * `suffix`: optional shirt description or numbering of the test case.
  * `model`: node type of moz.l10n.model data model
    (currently `Message` only but to be explicit and extended)
  * `format_ext`: ".ftl", ".mf2" ... the according string suffix for the format.
  * `type`: One of these:
    * "target": This is a translation file.
    * "source": This is a reference file.
    * "expected": This is a snapshot file in JSON format.

This way cases are listed in one bunch, we can have arbitrary numbers of cases
per format and descriptive names, if we want or just have test1, test2, ...
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

import moz.l10n.formats
import moz.l10n.lint
import pytest
from moz.l10n.formats import Format, mf2
from moz.l10n.message import parse_message
from moz.l10n.model import Message

# from moz.l10n.lint.tools import iter_placeholders

TEST_EXTENSIONS = moz.l10n.formats.l10n_extensions.union({".webext", ".mf2"})
CUSTOM_FORMAT_MAP = {
    ".xml": Format.android,
    ".mf2": Format.mf2,
    ".webext": Format.webext,
    ".json": Format.plain_json,
}


def run_from_main() -> None:
    """Run according tests from calling `__main__` module.

    Gather rule classes from calling module.
    Assemble list of pytest instructions to test exactly these rules.
    Invoke `pytest.main` with that list.
    """
    template = (
        f"{moz.l10n.lint.PY_ROOT / 'tests' / 'test_lint_rules.py'}::test_rule[{{}}]"
    )
    rule_module = sys.modules["__main__"]
    test_stack: list[str] = []
    for rule_cls in moz.l10n.lint.iter_rule_classes(rule_module):
        test_stack.append(template.format(moz.l10n.lint.get_full_name(rule_cls)))
    pytest.main(test_stack)


def iter_test_messages(
    rule_path: Path,
) -> Iterator[tuple[Message, Message, Path, Format, str]]:
    """Loop over all tested format extensions,
    Yield targe, source messages, the target path, the format and snapshot name per found case.
    """
    for ext in TEST_EXTENSIONS:
        for target_path in rule_path.glob(f"test*.message.target{ext}"):
            stem = target_path.stem[:-7]
            source_path = rule_path / f"{stem}.source{ext}"
            if not source_path.is_file():
                continue

            target_str = target_path.read_text()
            source_str = source_path.read_text()
            if not target_str and not source_str:
                continue

            resource_format = get_format(
                target_path if target_str else source_path, target_str or source_str
            )
            assert resource_format is not None, (
                f"Could not detect format of files\n  {target_path}\n  {source_path}"
            )

            target = _parse_test_data(resource_format, target_str)
            source = _parse_test_data(resource_format, source_str)
            snapshot_name = f"{stem}.expected{ext}.json"
            yield target, source, target_path, resource_format, snapshot_name


def _parse_test_data(
    resource_format: Format,
    raw_str: str,
) -> Message:
    """Parse testing data according to `resource_format`.
    If failing: retry with `mf2_parse_message`. We're not testing parsing here.
    This is for data that breaks the native formats parser.
    """
    placeholders = None
    if resource_format is Format.webext:
        # TODO: this is a dilemma!
        # The "unsupported" case from Pontoon is actually uncovered in its own test!
        # Putting it in place is hard because a placeholder that would trigger the check
        # would already trip the webext parser before we get to checking!
        # The trick now is to parse via mf2 and pass it on.
        # placeholders = {}
        # for i, match in enumerate(iter_placeholders(raw_str, resource_format), 1):
        #     placeholders[match[0].strip("$").lower()] = {"content": f"${i}"}
        return mf2.mf2_parse_message(raw_str)

    return parse_message(resource_format, raw_str, webext_placeholders=placeholders)


def get_format(path: Path, raw_source: str) -> Format | None:
    """From path get dedicated resource `Format` enum entry.
    * Testing lint we'll use ".xliff" explicitly. Any `.xml` is android!
    * For JSON because our resources are `Messages` only and no proper JSON syntax:
        * We invent a dedicated `.webext` extension and
        * use `.json` for "plain_json" for any other JSON.
    """
    return CUSTOM_FORMAT_MAP.get(
        path.suffix, moz.l10n.formats.detect_format(path.name, raw_source)
    )
