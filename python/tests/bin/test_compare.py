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
import os
from tempfile import TemporaryDirectory

import moz.l10n.bin
import pytest
from click.testing import CliRunner

from ..utils import Tree, build_file_tree

FILE = "file.ftl"
SOURCE = "source.json"


def test_compare_missing_messages() -> None:
    """Test proper occurrence "missing" and "errors" in output report."""
    source_map = {FILE: ["msg-a", "msg-b", "msg-c"]}
    fr_ftl = "msg-a = Bonjour\nmsg-b = Monde"
    tree: Tree = {SOURCE: json.dumps(source_map), "fr": {FILE: fr_ftl}}
    with TemporaryDirectory() as tmp_dir:
        build_file_tree(tmp_dir, tree)
        source_json_path = os.path.join(tmp_dir, SOURCE)
        fr_dir = os.path.join(tmp_dir, "fr")

        runner = CliRunner()
        args = ["compare", fr_dir, "--source", source_json_path]
        result = runner.invoke(moz.l10n.bin.cli, args)

        assert result.exit_code == 0
        assert "source: 3" in result.output
        assert "fr: -1" in result.output

        # test same with INFO level logging paths
        result = runner.invoke(moz.l10n.bin.cli, [*args, "--verbose"])
        assert FILE in result.output
        # test same with DEBUG level logging messages
        result = runner.invoke(moz.l10n.bin.cli, [*args, "-vv"])
        assert "msg-c" in result.output

        result = runner.invoke(
            moz.l10n.bin.cli,
            ["compare", fr_dir, "--json", "--source", source_json_path],
        )
        assert result.exit_code == 0
        parsed_output = json.loads(result.output)
        assert "fr" in parsed_output
        assert parsed_output["fr"]["missing"] == {FILE: ["msg-c"]}
        assert parsed_output["fr"]["errors"] is None


def test_compare_multiple_paths() -> None:
    """Test passing a number of paths to be compared
    and using short relative paths to work.
    """
    locales = "fr", "es", "nb-NO", "de"
    tree: Tree = {locale: {FILE: "msg-a = Translated\n"} for locale in locales}
    tree[SOURCE] = json.dumps({FILE: ["msg-a"]})

    with TemporaryDirectory() as tmp_dir:
        build_file_tree(tmp_dir, tree)
        cwd = os.getcwd()
        try:
            os.chdir(tmp_dir)

            runner = CliRunner()
            args = ["compare", *locales, "--source", SOURCE]
            result = runner.invoke(moz.l10n.bin.cli, [*args, "--json"])

            assert result.exit_code == 0
            json_output = json.loads(result.output)
            assert all(locale in json_output for locale in locales)

            # testing again with some changes
            with open(
                os.path.join(tmp_dir, "de", FILE), "w", encoding="utf8"
            ) as file_obj:
                file_obj.write("!@$%!@#$")
            os.unlink(os.path.join(tmp_dir, "nb-NO", FILE))

            result = runner.invoke(moz.l10n.bin.cli, args)
            assert "!!!" in result.output

            result = runner.invoke(moz.l10n.bin.cli, [*args, "--json"])
            json_output = json.loads(result.output)

        finally:
            os.chdir(cwd)

        assert json_output["nb-NO"]["missing"] == {FILE: ["msg-a"]}
        assert all(
            json_output[locale]["missing"] is None
            for locale in locales
            if locale != "nb-NO"
        )
        assert json_output["de"]["errors"] is not None
        assert all(
            json_output[locale]["errors"] is None
            for locale in locales
            if locale != "de"
        )


def test_compare_ext_inclusion_and_exclusion() -> None:
    """Test source having keys spread across different file types."""
    source_map = {FILE: ["msg-ftl"], "file.ini": ["msg-ini"], "file.txt": ["msg-txt"]}

    with TemporaryDirectory() as tmp_dir:
        source_json_path = os.path.join(tmp_dir, SOURCE)
        with open(source_json_path, "w", encoding="utf-8") as f:
            json.dump(source_map, f)

        fr_dir = os.path.join(tmp_dir, "fr")
        os.makedirs(fr_dir, exist_ok=True)

        # Write files but leave them empty so keys count as missing
        extensions = "ftl", "ini", "txt"
        paths = tuple(os.path.join(fr_dir, f"file.{ext}") for ext in extensions)
        for path in paths:
            with open(path, "w", encoding="utf-8") as f:
                f.write("")

        runner = CliRunner()
        cmd_stem = ["compare", fr_dir, "--source", source_json_path, "--ext"]

        # Test counting messages only from included extensions
        result = runner.invoke(moz.l10n.bin.cli, [*cmd_stem, ".ftl,ini"])
        assert result.exit_code == 0
        assert "source: 2" in result.output

        result = runner.invoke(moz.l10n.bin.cli, [*cmd_stem, "ini"])
        assert result.exit_code == 0
        assert "source: 1" in result.output

        # Exclusion with '!' - look at everything EXCEPT .txt
        result = runner.invoke(moz.l10n.bin.cli, [*cmd_stem, "!txt,!"])
        assert result.exit_code == 0
        # Source total should drop .txt messages (3 total - 1 txt = 2)
        assert "source: 2" in result.output


def test_ext_settify() -> None:
    """Explicitly test the settifyer."""
    func = moz.l10n.bin.compare._ext_settify

    ext = "txt"
    in_set, ex_set = func(None, None, ext)  # ty:ignore[invalid-argument-type]
    assert in_set == set([".txt"])
    assert ex_set == set()

    ext = "'.ftl,!txt, ini'"
    in_set, ex_set = func(None, None, ext)  # ty:ignore[invalid-argument-type]
    assert in_set == set([".ftl", ".ini"])
    assert ex_set == set([".txt"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
