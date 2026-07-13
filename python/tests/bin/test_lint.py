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

import moz.l10n.bin
import pytest
from click.testing import CliRunner

from ..utils import Tree, build_file_tree


def test_help() -> None:
    runner = CliRunner()
    result = runner.invoke(moz.l10n.bin.cli, ["lint", "--help"])
    assert result.exit_code == 0


def test_no_args() -> None:
    # `paths` is a required argument, so click itself rejects an empty invocation.
    runner = CliRunner()
    result = runner.invoke(moz.l10n.bin.cli, ["lint"])
    assert result.exit_code == 2


def test_ok_glob() -> None:
    tree: Tree = {
        "a.ftl": "a = A\n",
        "b.ftl": "b = B\n",
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["lint", join(root, "*.ftl")])
        assert result.exit_code == 0


def test_parse_failure() -> None:
    tree: Tree = {
        "good.ftl": "very-good = Sehr gut!\n",
        "bad.ftl": "= this is not a valid message\n",
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["lint", join(root, "*.ftl")])
        assert result.exit_code == 1


def test_unsupported() -> None:
    """Test unknown extensions reported as unsupported -> exit 1.
    Unless it's explicitly skipped -> exit 0.
    """
    tree: Tree = {"notes.txt": "just some text\n"}
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()

        result = runner.invoke(moz.l10n.bin.cli, ["lint", join(root, "notes.txt")])
        assert result.exit_code == 1

        result = runner.invoke(
            moz.l10n.bin.cli, ["lint", "--skip-unknown", join(root, "notes.txt")]
        )
        assert result.exit_code == 0


def test_directory() -> None:
    tree: Tree = {
        "en-US": {"a.ftl": "a = A\n"},
        "fr": {"a.ftl": "a = A\n"},
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["lint", root])
        assert result.exit_code == 0


def test_config_with_paths() -> None:
    tree: Tree = {
        "l10n.toml": "",
        "a.ftl": "a = A\n",
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)

        runner = CliRunner()
        # --config combined with paths is an argument error.
        result = runner.invoke(
            moz.l10n.bin.cli,
            ["lint", "--config", join(root, "l10n.toml"), join(root, "a.ftl")],
        )
        assert result.exit_code == 2
        # --config WITHOUT paths works.
        result = runner.invoke(
            moz.l10n.bin.cli, ["lint", "--config", join(root, "l10n.toml")]
        )
        assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
