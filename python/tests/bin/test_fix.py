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

from os.path import join
from tempfile import TemporaryDirectory
from textwrap import dedent

import moz.l10n.bin
import pytest
from click.testing import CliRunner

from ..utils import Tree, build_file_tree


def test_help() -> None:
    runner = CliRunner()
    result = runner.invoke(moz.l10n.bin.cli, ["fix", "--help"])
    assert result.exit_code == 0


def test_wrong_args() -> None:
    """Test `paths` or `config` being required."""
    runner = CliRunner()
    # Test none
    result = runner.invoke(moz.l10n.bin.cli, ["fix"])
    assert result.exit_code == 2

    tree: Tree = {"a.ftl": "a = A\n"}
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        # Test both
        result = runner.invoke(
            moz.l10n.bin.cli,
            ["fix", "--config", join(root, "l10n.toml"), join(root, "a.ftl")],
        )
        assert result.exit_code == 2


def test_already_formatted() -> None:
    """Test already formatted file being left untouched."""
    tree: Tree = {"a.ftl": "a = A\n"}
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["fix", join(root, "*.ftl")])
        assert result.exit_code == 0

        with open(join(root, "a.ftl")) as file:
            assert file.read() == "a = A\n"


def test_directory() -> None:
    """Test passing in a directory path."""
    tree: Tree = {
        "en-US": {"a.ftl": "a = A\n"},
        "fr": {"a.ftl": "a = A\n"},
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["fix", root])
        assert result.exit_code == 0


def test_reformats() -> None:
    """Test poorly formatted file being rewritten in canonical form."""
    tree: Tree = {"a.ftl": "a=A"}
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["fix", join(root, "*.ftl")])
        assert result.exit_code == 0

        with open(join(root, "a.ftl")) as file:
            assert file.read() == "a = A\n"


def test_parse_failure() -> None:
    tree: Tree = {"bad.ftl": "= this is not a valid message\n"}
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["fix", join(root, "*.ftl")])
        assert result.exit_code == 1


def test_unsupported() -> None:
    """Test unknown extensions being skipped as unsupported.
    Not an error -> exit 0.
    """
    tree: Tree = {"notes.txt": "just some text\n"}
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["fix", join(root, "notes.txt")])
        assert result.exit_code == 0


def test_config() -> None:
    """Test using `--config` arg explicitly."""
    cfg_toml = dedent(
        """
        locales = ["fr"]
        [[paths]]
            reference = "en-US/**/*.ftl"
            l10n = "{locale}/**/*.ftl"
        """
    )
    tree: Tree = {
        "l10n.toml": cfg_toml,
        "en-US": {"a.ftl": "a=A"},
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(
            moz.l10n.bin.cli, ["fix", "--config", join(root, "l10n.toml")]
        )
        assert result.exit_code == 0

        with open(join(root, "en-US", "a.ftl")) as file:
            assert file.read() == "a = A\n"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
