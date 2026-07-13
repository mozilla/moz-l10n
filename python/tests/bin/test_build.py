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
import logging
from os.path import exists, join
from tempfile import TemporaryDirectory
from textwrap import dedent

import moz.l10n.bin
import pytest
from click.testing import CliRunner
from moz.l10n.bin import build
from moz.l10n.formats import Format
from moz.l10n.model import Comment, Entry, PatternMessage, Resource, Section

from ..utils import Tree, build_file_tree

CFG_TOML = """
basepath = "."
locales = ["fr"]
[[paths]]
    reference = "en/file.ftl"
    l10n = "{locale}/file.ftl"
"""


def test_write_target_file_fluent() -> None:
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


def test_write_target_file_nonfluent() -> None:
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


def test_write_target_file_multipart_id() -> None:
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


def test_cli_writes_coverage_json() -> None:
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
        "l10n.toml": dedent("""
            basepath = "."
            locales = ["fr", "de"]
            [[paths]]
                reference = "en/file.ftl"
                l10n = "{locale}/file.ftl"
        """),
        "en": {"file.ftl": source_ftl},
        "fr": {"file.ftl": fr_ftl},
        "de": {"file.ftl": de_ftl},
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
            "--locales", '"fr, de"',
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


def test_cli_skips_coverage_without_flag() -> None:
    tree: Tree = {
        "l10n.toml": CFG_TOML,
        "en": {"file.ftl": "msg-a = src\n"},
        "fr": {"file.ftl": "msg-a = fr\n"},
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
        ])
        # fmt: on
        assert result.exit_code == 0
        assert not exists(join(target, "fr", "coverage.json"))


def test_cli_verbosity() -> None:
    """Test different and default log levels set by -v or --verbose."""
    tree: Tree = {
        "l10n.toml": CFG_TOML,
        "en": {"file.ftl": "msg-a = src\n"},
        "fr": {"file.ftl": "msg-a = fr\n"},
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)
        target = join(root, "out")
        # fmt: off
        args = [
            "--config", join(root, "l10n.toml"),
            "--base", root, "--target", target,
            "--locales", "fr"
        ]
        # fmt: on
        runner = CliRunner()
        # Test no logging.
        result = runner.invoke(moz.l10n.bin.cli, ["build", *args])
        assert result.exit_code == 0
        assert result.output == ""

        # Test DEBUG logging. "build" will put "source " first.
        del logging.root.handlers[:]
        result = runner.invoke(moz.l10n.bin.cli, ["build", "-vv", *args])
        assert result.exit_code == 0
        assert result.output.startswith("source ")

        # Test INFO logging.
        del logging.root.handlers[:]
        result = runner.invoke(moz.l10n.bin.cli, ["build", "-v", *args])
        assert result.exit_code == 0
        assert not result.output.startswith("source ")
        assert result.output != ""

        del logging.root.handlers[:]
        result = runner.invoke(moz.l10n.bin.cli, ["build", "--verbose", *args])
        assert result.exit_code == 0


def test_locales_settify() -> None:
    """Explicitly test the settifyer."""
    func = moz.l10n.bin.build._locales_settify

    locales = "en"
    result = func(None, None, locales)  # ty:ignore[invalid-argument-type]
    assert result == set(["en"])

    locales = ""
    result = func(None, None, locales)  # ty:ignore[invalid-argument-type]
    assert result == set([])

    locales = "'fr,de,,nb-NO'"
    result = func(None, None, locales)  # ty:ignore[invalid-argument-type]
    assert result == set(["fr", "de", "nb-NO"])

    locales = "fr, en, nb-NO "
    result = func(None, None, locales)  # ty:ignore[invalid-argument-type]
    assert result == set(["fr", "en", "nb-NO"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
