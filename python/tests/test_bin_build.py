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

import pytest
from click.testing import CliRunner
from moz.l10n.bin import build, cli
from moz.l10n.formats import Format
from moz.l10n.model import Comment, Entry, PatternMessage, Resource, Section

from .utils import Tree, build_file_tree


def test_write_target_file_fluent():
    entries: list[Entry[PatternMessage] | Comment] = [
        Entry(("msg-a",), PatternMessage(["s"])),
        Entry(("msg-b",), PatternMessage(["s"]), {"attr": PatternMessage(["s"])}),
        Entry(("msg-c",), PatternMessage(["s"]), {"attr": PatternMessage(["s"])}),
        Entry(("-term-a",), PatternMessage(["s"])),
        Entry(("-term-b",), PatternMessage(["s"]), {"attr": PatternMessage(["s"])}),
        Entry(("-term-c",), PatternMessage(["s"])),
    ]
    source_res = Resource(Format.fluent, [Section((), entries)])
    l10n_src = dedent("""\
        msg-a = tgt
            .extra = tgt
        msg-b = tgt
            .attr = tgt
            .extra = tgt
        msg-c = tgt
            .extra = tgt
        -term-a = tgt
            .extra = tgt
        -term-b = tgt
            .extra = tgt
        -term-x = tgt
            .extra = tgt
        """)
    with TemporaryDirectory() as tmpdir:
        l10n_path = join(tmpdir, "l10n.ftl")
        tgt_path = join(tmpdir, "tgt.ftl")
        with open(l10n_path, mode="w") as file:
            file.write(l10n_src)
        msg_delta, total_count, missing_ids = build.write_target_file(
            "", source_res, l10n_path, tgt_path
        )
        with open(tgt_path, mode="r") as file:
            tgt_src = file.read()
        assert tgt_src == dedent("""\
            msg-a = tgt
            msg-b = tgt
                .attr = tgt
            -term-a = tgt
                .extra = tgt
            -term-b = tgt
                .extra = tgt
            """)
        assert msg_delta == -2
        assert total_count == 6
        assert missing_ids == ["msg-c", "-term-c"]


def test_write_target_file_nonfluent():
    entries: list[Entry[PatternMessage] | Comment] = [
        Entry(("msg-a",), PatternMessage(["s"])),
        Entry(("msg-b",), PatternMessage(["s"]), {"attr": PatternMessage(["s"])}),
        Entry(("msg-c",), PatternMessage(["s"]), {"attr": PatternMessage(["s"])}),
        Entry(("-term-a",), PatternMessage(["s"])),
        Entry(("-term-b",), PatternMessage(["s"]), {"attr": PatternMessage(["s"])}),
        Entry(("-term-c",), PatternMessage(["s"])),
    ]
    # A bit hacky, but works for test purposes
    source_res = Resource(Format.plain_json, [Section((), entries)])
    l10n_src = dedent("""\
        msg-a = tgt
            .extra = tgt
        msg-b = tgt
            .attr = tgt
            .extra = tgt
        msg-c = tgt
            .extra = tgt
        -term-a = tgt
            .extra = tgt
        -term-b = tgt
            .extra = tgt
        -term-x = tgt
            .extra = tgt
        """)
    with TemporaryDirectory() as tmpdir:
        l10n_path = join(tmpdir, "l10n.ftl")
        tgt_path = join(tmpdir, "tgt.ftl")
        with open(l10n_path, mode="w") as file:
            file.write(l10n_src)
        msg_delta, total_count, missing_ids = build.write_target_file(
            "", source_res, l10n_path, tgt_path
        )
        with open(tgt_path, mode="r") as file:
            tgt_src = file.read()
        assert tgt_src == dedent("""\
            msg-a = tgt
                .extra = tgt
            msg-b = tgt
                .attr = tgt
                .extra = tgt
            msg-c = tgt
                .extra = tgt
            -term-a = tgt
                .extra = tgt
            -term-b = tgt
                .extra = tgt
            -term-c = s
            """)
        assert msg_delta == 1
        assert total_count == 6
        assert missing_ids == ["-term-c"]


def test_write_target_file_multipart_id():
    # INI sections produce two-part ids, kept as a list rather than joined.
    entries: list[Entry[PatternMessage] | Comment] = [
        Entry(("WelcomeText",), PatternMessage(["s"])),
        Entry(("LicenseText",), PatternMessage(["s"])),
    ]
    source_res = Resource(Format.ini, [Section(("Strings",), entries)])
    l10n_src = "[Strings]\nWelcomeText = tgt\n"
    with TemporaryDirectory() as tmpdir:
        l10n_path = join(tmpdir, "l10n.ini")
        tgt_path = join(tmpdir, "tgt.ini")
        with open(l10n_path, mode="w") as file:
            file.write(l10n_src)
        msg_delta, total_count, missing_ids = build.write_target_file(
            "", source_res, l10n_path, tgt_path
        )
        assert msg_delta == 1
        assert total_count == 2
        assert missing_ids == [["Strings", "LicenseText"]]


def test_cli_writes_coverage_json():
    cfg_toml = dedent(
        """
        basepath = "."
        locales = ["fr", "de"]
        [[paths]]
            reference = "en/file.ftl"
            l10n = "{locale}/file.ftl"
        """
    )
    source_ftl = dedent("""\
        msg-a = src
        msg-b = src
        msg-c = src
        msg-d = src
        """)
    fr_ftl = dedent("""\
        msg-a = fr
        msg-b = fr
        msg-c = fr
        msg-d = fr
        """)
    de_ftl = dedent("""\
        msg-a = de
        msg-b = de
        """)
    tree: Tree = {
        "l10n.toml": cfg_toml,
        "en": {"file.ftl": source_ftl},
        "fr": {"file.ftl": fr_ftl},
        "de": {"file.ftl": de_ftl},
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)
        target = join(root, "out")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(cli, ["build",
            "--config", join(root, "l10n.toml"),
            "--base", root,
            "--target", target,
            "--locales", "fr", "de",
            "--coverage",
        ])
        # fmt: on
        assert result.exit_code == 0

        with open(join(target, "fr", "coverage.json"), encoding="utf-8") as f:
            fr_coverage = json.load(f)
        with open(join(target, "de", "coverage.json"), encoding="utf-8") as f:
            de_coverage = json.load(f)

        assert fr_coverage == {"file.ftl": {"total": 4, "missing": []}}
        assert de_coverage == {"file.ftl": {"total": 4, "missing": ["msg-c", "msg-d"]}}


def test_cli_skips_coverage_without_flag():
    cfg_toml = dedent(
        """
        basepath = "."
        locales = ["fr"]
        [[paths]]
            reference = "en/file.ftl"
            l10n = "{locale}/file.ftl"
        """
    )
    tree: Tree = {
        "l10n.toml": cfg_toml,
        "en": {"file.ftl": "msg-a = src\n"},
        "fr": {"file.ftl": "msg-a = fr\n"},
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)
        target = join(root, "out")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(cli, ["build",
            "--config", join(root, "l10n.toml"),
            "--base", root,
            "--target", target,
            "--locales", "fr",
        ])
        # fmt: on
        assert result.exit_code == 0
        assert not exists(join(target, "fr", "coverage.json"))


def test_coverage_merge():
    src = "msg-a = src\nmsg-b = src\nmsg-c = src\n"
    l10n = "msg-a = fr\nmsg-b = fr\n"
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.ftl": src, "fr.ftl": l10n})
        target = join(root, "file.ftl")
        coverage = join(root, "coverage.json")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(cli, ["build-file",
            "--source", join(root, "en.ftl"),
            "--l10n", join(root, "fr.ftl"),
            "--target", target,
            "--coverage-base", root,
        ])
        # fmt: on
        assert result.exit_code == 0

        with open(coverage, encoding="utf-8") as f:
            assert json.load(f) == {"file.ftl": {"total": 3, "missing": ["msg-c"]}}


def test_coverage_updates_existing_file():
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
        result = runner.invoke(cli, ["build-file",
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


def test_coverage_source_only():
    src = "msg-a = src\nmsg-b = src\n"
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.ftl": src})
        target = join(root, "file.ftl")
        coverage = join(root, "coverage.json")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(cli, ["build-file",
            "--source", join(root, "en.ftl"),
            "--target", target,
            "--coverage-base", root,
        ])
        # fmt: on
        assert result.exit_code == 0

        with open(coverage, encoding="utf-8") as f:
            assert json.load(f) == {"file.ftl": {"total": 2, "missing": []}}


def test_coverage_unparseable_source():
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.txt": "not a known format\n"})
        target = join(root, "file.txt")
        coverage = join(root, "coverage.json")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(cli, ["build-file",
            "--source", join(root, "en.txt"),
            "--target", target,
            "--coverage-base", root,
        ])
        # fmt: on
        assert result.exit_code == 0

        with open(coverage, encoding="utf-8") as f:
            assert json.load(f) == {"file.txt": {"total": 0, "missing": []}}


def test_coverage_matches_l10n_build():
    # A coverage.json first created by l10n-build is then updated by
    # l10n-build-file for one resource. With --coverage-base set to the
    # locale dir, the key is derived as target's relative path, so the
    # entry is overwritten in place rather than added under a divergent
    # (absolute) path.
    cfg_toml = dedent(
        """
        basepath = "."
        locales = ["fr"]
        [[paths]]
            reference = "en/file.ftl"
            l10n = "{locale}/file.ftl"
        """
    )
    source_ftl = "msg-a = src\nmsg-b = src\nmsg-c = src\n"
    fr_ftl = "msg-a = fr\n"
    tree: Tree = {
        "l10n.toml": cfg_toml,
        "en": {"file.ftl": source_ftl},
        "fr": {"file.ftl": fr_ftl},
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)
        target = join(root, "out")
        # fmt: off
        runner = CliRunner()
        result = runner.invoke(cli, ["build",
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
        runner = CliRunner()
        result = runner.invoke(cli, ["build-file",
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


def test_skips_coverage_without_flag():
    src = "msg-a = src\n"
    with TemporaryDirectory() as root:
        build_file_tree(root, {"en.ftl": src})
        target = join(root, "out.ftl")

        # fmt: off
        runner = CliRunner()
        result = runner.invoke(cli, ["build-file",
            "--source", join(root, "en.ftl"),
            "--target", target,
        ])
        # fmt: on
        assert result.exit_code == 0

        assert not exists(join(root, "coverage.json"))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
