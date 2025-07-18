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
from unittest import TestCase

from moz.l10n.bin.build import write_target_file
from moz.l10n.formats import Format
from moz.l10n.model import Comment, Entry, PatternMessage, Resource, Section


class TestBuild(TestCase):
    def test_write_target_file_fluent(self):
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
            msg_delta = write_target_file("", source_res, l10n_path, tgt_path)
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

    def test_write_target_file_nonfluent(self):
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
            msg_delta = write_target_file("", source_res, l10n_path, tgt_path)
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
