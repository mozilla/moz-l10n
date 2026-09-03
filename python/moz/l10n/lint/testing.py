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

import sys
from pathlib import Path
from typing import Iterator

import moz.l10n.formats
import moz.l10n.lint
import pytest
from moz.l10n.formats import mf2
from moz.l10n.message import parse_message
from moz.l10n.model import Format, Message

# from moz.l10n.lint.tools import iter_placeholders

SOURCE_NAME = "source"
TARGET_NAME = "example"
TEST_EXTENSIONS = moz.l10n.formats.l10n_extensions.union({".webext"})


def run_from_main():
    template = (
        f"{moz.l10n.lint.PY_ROOT / 'tests' / 'test_lint_rules.py'}::test_rule[{{}}]"
    )
    rule_module = sys.modules["__main__"]
    test_stack: list[str] = []
    for rule_cls in moz.l10n.lint.iter_rule_classes(rule_module):
        test_stack.append(template.format(rule_cls.get_full_name()))
    pytest.main(test_stack)


def iter_test_files(
    rule_path: Path,
) -> Iterator[tuple[Message | None, Message | None, Path, Format]]:
    for ext in TEST_EXTENSIONS:
        target_path = rule_path / f"{TARGET_NAME}{ext}"
        source_path = rule_path / f"{SOURCE_NAME}{ext}"
        if not target_path.is_file() and not source_path.is_file():
            continue

        target_str = target_path.read_text() if target_path.is_file() else ""
        source_str = source_path.read_text() if source_path.is_file() else ""
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
        yield target, source, target_path, resource_format


def _parse_test_data(
    resource_format: Format,
    raw_str: str,
) -> Message | None:
    """Parse testing data according to `resource_format`.
    If failing retry with `mf2_parse_message`. We're not testing parsing here.
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
    * Testing lint we'll use .xliff explicitly. Any `.xml` is android!
    * For JSON because our resources are `Messages` only and no proper JSON syntax:
        * We invent a dedicated `.webext` extension and
        * use `.json` for "plain_json" for any other JSON.
    """
    if path.suffix == ".xml":
        return Format.android
    if path.suffix == ".webext":
        return Format.webext
    if path.suffix == ".json":
        return Format.plain_json
    return moz.l10n.formats.detect_format(path.name, raw_source)
