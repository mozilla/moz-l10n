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
from os.path import exists, join
from tempfile import TemporaryDirectory
from textwrap import dedent

import moz.l10n.bin
import pytest
from click.testing import CliRunner

from ..utils import Tree, build_file_tree


def test_coverage_merge() -> None:
    src = "msg-a = src\nmsg-b = src\nmsg-c = src\n"
    l10n = "msg-a = fr\nmsg-b = fr\n"
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.ftl": src, "fr.ftl": l10n})
        target = join(root, "file.ftl")
        coverage = join(root, "coverage.json")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en.ftl"),
            "--l10n", join(root, "fr.ftl"),
            "--target", target,
            "--coverage-base", root,
        ])
        # fmt: on
        assert result.exit_code == 0

        with open(coverage, encoding="utf-8") as f:
            assert json.load(f) == {"file.ftl": {"total": 3, "missing": ["msg-c"]}}


def test_coverage_updates_existing_file() -> None:
    # fastermake builds one resource at a time, sharing the per-locale
    # coverage.json: the existing entries are preserved and the current
    # resource's entry is added/overwritten.
    src = "msg-a = src\nmsg-b = src\n"
    l10n = "msg-a = fr\n"
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.ftl": src, "fr.ftl": l10n})
        target = join(root, "file.ftl")
        coverage = join(root, "coverage.json")
        with open(coverage, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "other.ftl": {"total": 5, "missing": []},
                    "file.ftl": {"total": 1, "missing": ["stale"]},
                },
                f,
            )
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en.ftl"),
            "--l10n", join(root, "fr.ftl"),
            "--target", target,
            "--coverage-base", root,
        ])
        # fmt: on
        assert result.exit_code == 0

        with open(coverage, encoding="utf-8") as f:
            assert json.load(f) == {
                "other.ftl": {"total": 5, "missing": []},
                "file.ftl": {"total": 2, "missing": ["msg-b"]},
            }


def test_coverage_source_only() -> None:
    src = "msg-a = src\nmsg-b = src\n"
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.ftl": src})
        target = join(root, "file.ftl")
        coverage = join(root, "coverage.json")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en.ftl"),
            "--target", target,
            "--coverage-base", root,
        ])
        # fmt: on
        assert result.exit_code == 0

        with open(coverage, encoding="utf-8") as f:
            assert json.load(f) == {"file.ftl": {"total": 2, "missing": []}}


def test_coverage_unparseable_source() -> None:
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.txt": "not a known format\n"})
        target = join(root, "file.txt")
        coverage = join(root, "coverage.json")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en.txt"),
            "--target", target,
            "--coverage-base", root,
        ])
        # fmt: on
        assert result.exit_code == 0

        with open(coverage, encoding="utf-8") as f:
            assert json.load(f) == {"file.txt": {"total": 0, "missing": []}}


def test_coverage_matches_l10n_build() -> None:
    # A coverage.json first created by l10n-build is then updated by
    # l10n-build-file for one resource. With --coverage-base set to the
    # locale dir, the key is derived as target's relative path, so the
    # entry is overwritten in place rather than added under a divergent
    # (absolute) path.
    source_ftl = "msg-a = src\nmsg-b = src\nmsg-c = src\n"
    fr_ftl = "msg-a = fr\n"
    tree: Tree = {
        "l10n.toml": dedent("""
            basepath = "."
            locales = ["fr"]
            [[paths]]
                reference = "en/file.ftl"
                l10n = "{locale}/file.ftl"
        """),
        "en": {"file.ftl": source_ftl},
        "fr": {"file.ftl": fr_ftl},
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)
        target = join(root, "out")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["build",
            "--config", join(root, "l10n.toml"),
            "--base", root,
            "--target", target,
            "--locales", "fr",
            "--coverage",
        ])
        # fmt: on
        assert result.exit_code == 0

        coverage = join(target, "fr", "coverage.json")
        with open(coverage, encoding="utf-8") as f:
            assert json.load(f) == {
                "file.ftl": {"total": 3, "missing": ["msg-b", "msg-c"]}
            }

        # Re-localize the same file with a more complete translation.
        fr_full = join(root, "fr", "file.ftl")
        with open(fr_full, "w", encoding="utf-8") as f:
            f.write("msg-a = fr\nmsg-b = fr\n")

        # fmt: off
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en", "file.ftl"),
            "--l10n", fr_full,
            "--target", join(target, "fr", "file.ftl"),
            "--coverage-base", join(target, "fr"),
        ])
        # fmt: on
        assert result.exit_code == 0

        with open(coverage, encoding="utf-8") as f:
            # Same key updated in place, no stale duplicate entry.
            assert json.load(f) == {"file.ftl": {"total": 3, "missing": ["msg-c"]}}


def test_skips_coverage_without_flag() -> None:
    src = "msg-a = src\n"
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.ftl": src})
        target = join(root, "out.ftl")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en.ftl"),
            "--target", target,
        ])
        # fmt: on
        assert result.exit_code == 0
        assert not exists(join(root, "coverage.json"))


def test_merge_target_content() -> None:
    """Test built-file targets for having:
    * trimmed comments
    * l10n applied
    * dropped msgs not in localization
    """
    comment = "# Ein Kommentar!\n"
    src = "msg-a = src\nmsg-b = src\n"
    l10n = "msg-a = fr\n"
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.ftl": f"{comment}{src}", "fr.ftl": l10n})
        target = join(root, "out.ftl")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en.ftl"),
            "--l10n", join(root, "fr.ftl"),
            "--target", target,
        ])
        # fmt: on
        assert result.exit_code == 0
        with open(target, encoding="utf-8") as f:
            assert f.read() == l10n

        # fmt: off
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en.ftl"),
            "--target", target,
        ])
        # fmt: on
        assert result.exit_code == 0
        with open(target, encoding="utf-8") as f:
            assert f.read() == src


def test_unparseable_source_copies_l10n() -> None:
    """Test unsupported source format copies --l10n file verbatim when present."""
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.txt": "SRC\n", "fr.txt": "L10N\n"})
        target = join(root, "out.txt")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en.txt"),
            "--l10n", join(root, "fr.txt"),
            "--target", target,
        ])
        # fmt: on
        assert result.exit_code == 0
        with open(target, encoding="utf-8") as f:
            assert f.read() == "L10N\n"


def test_unparseable_source_copies_source() -> None:
    """Test unsupported source fallback to copy source."""
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.txt": "SRC\n"})
        target = join(root, "out.txt")
        runner = CliRunner()
        # fmt: off
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en.txt"),
            "--target", target,
        ])
        # fmt: on
        assert result.exit_code == 0
        with open(target, encoding="utf-8") as f:
            assert f.read() == "SRC\n"


def test_unparseable_l10n_exits_nonzero() -> None:
    """Test parse failure on l10n file is reported as a fatal error (exit 1)."""
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.ftl": "msg-a = A\n", "fr.txt": "junk\n"})
        target = join(root, "out.ftl")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(moz.l10n.bin.cli, ["build-file",
            "--source", join(root, "en.ftl"),
            "--l10n", join(root, "fr.txt"),
            "--target", target,
        ])
        # fmt: on
        assert result.exit_code == 1
        assert isinstance(result.exception, SystemExit)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
