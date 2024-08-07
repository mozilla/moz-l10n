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

from textwrap import dedent
from unittest import TestCase

from moz.l10n.message import PatternMessage
from moz.l10n.resource.data import Comment, Entry, Resource, Section
from moz.l10n.resource.format import Format
from moz.l10n.resource.ini import ini_parse, ini_serialize


class TestIni(TestCase):
    def test_section_comment(self):
        res = ini_parse(
            dedent(
                """\
                ; This file is in the UTF-8 encoding
                [Strings]
                TitleText=Some Title
                """
            )
        )
        assert res == Resource(
            Format.ini,
            [
                Section(
                    id=("Strings",),
                    entries=[Entry(("TitleText",), PatternMessage(["Some Title"]))],
                    comment="This file is in the UTF-8 encoding",
                )
            ],
        )
        assert "".join(ini_serialize(res)) == dedent(
            """\
            # This file is in the UTF-8 encoding
            [Strings]
            TitleText=Some Title
            """
        )
        assert (
            "".join(ini_serialize(res, trim_comments=True))
            == "[Strings]\nTitleText=Some Title\n"
        )

    def test_resource_comment(self):
        res = ini_parse(
            dedent(
                """\
                ; This Source Code Form is subject to the terms of the Mozilla Public
                ; License, v. 2.0. If a copy of the MPL was not distributed with this file,
                ; You can obtain one at http://mozilla.org/MPL/2.0/.
                ;
                ; This file is in the UTF-8 encoding

                [Strings]
                TitleText=Some Title
                """
            )
        )
        assert res == Resource(
            Format.ini,
            [
                Section(
                    id=("Strings",),
                    entries=[Entry(("TitleText",), PatternMessage(["Some Title"]))],
                )
            ],
            comment="This Source Code Form is subject to the terms of the Mozilla Public\n"
            "License, v. 2.0. If a copy of the MPL was not distributed with this file,\n"
            "You can obtain one at http://mozilla.org/MPL/2.0/.\n\n"
            "This file is in the UTF-8 encoding",
        )
        assert "".join(ini_serialize(res)) == dedent(
            """\
            # This Source Code Form is subject to the terms of the Mozilla Public
            # License, v. 2.0. If a copy of the MPL was not distributed with this file,
            # You can obtain one at http://mozilla.org/MPL/2.0/.
            #
            # This file is in the UTF-8 encoding

            [Strings]
            TitleText=Some Title
            """
        )
        assert (
            "".join(ini_serialize(res, trim_comments=True))
            == "[Strings]\nTitleText=Some Title\n"
        )

    def test_junk(self):
        with self.assertRaises(Exception):
            ini_parse(
                dedent(
                    """\
                    Junk
                    [Strings]
                    TitleText=Some Title
                    """
                )
            )

    def test_line_comment(self):
        res = ini_parse(
            dedent(
                """\
                [Strings] ; section comment
                ; entry pre comment
                TitleText=Some Title ; entry line comment
                    Continues
                """
            )
        )
        assert res == Resource(
            Format.ini,
            [
                Section(
                    id=("Strings",),
                    entries=[
                        Entry(
                            ("TitleText",),
                            PatternMessage(["Some Title\nContinues"]),
                            comment="entry pre comment\nentry line comment",
                        ),
                    ],
                    comment="section comment",
                )
            ],
        )
        assert "".join(ini_serialize(res)) == dedent(
            """\
            # section comment
            [Strings]
            # entry pre comment
            # entry line comment
            TitleText=Some Title
              Continues
            """
        )
        assert (
            "".join(ini_serialize(res, trim_comments=True))
            == "[Strings]\nTitleText=Some Title\n  Continues\n"
        )

    def test_trailing_comment(self):
        res = ini_parse(
            dedent(
                """\
                [Strings]
                TitleText=Some Title
                ;Stray trailing comment
                """
            )
        )
        assert res == Resource(
            Format.ini,
            [
                Section(
                    id=("Strings",),
                    entries=[
                        Entry(("TitleText",), PatternMessage(["Some Title"])),
                        Comment("Stray trailing comment"),
                    ],
                )
            ],
        )
        assert "".join(ini_serialize(res)) == dedent(
            """\
            [Strings]
            TitleText=Some Title

            # Stray trailing comment

            """
        )
        assert (
            "".join(ini_serialize(res, trim_comments=True))
            == "[Strings]\nTitleText=Some Title\n"
        )

    def test_empty_line_in_value(self):
        res = ini_parse(
            dedent(
                """\
                [Strings]
                TitleText=Some Title

                  Continues
                """
            )
        )
        assert res == Resource(
            Format.ini,
            [
                Section(
                    id=("Strings",),
                    entries=[
                        Entry(
                            ("TitleText",),
                            PatternMessage(["Some Title\n\nContinues"]),
                        )
                    ],
                )
            ],
        )
        assert "".join(ini_serialize(res)) == dedent(
            """\
            [Strings]
            TitleText=Some Title

              Continues
            """
        )

    def test_empty_value(self):
        res = ini_parse(
            dedent(
                """\
                [Strings]
                foo=
                bar=Bar
                """
            )
        )
        assert res == Resource(
            Format.ini,
            [
                Section(
                    id=("Strings",),
                    entries=[
                        Entry(("foo",), PatternMessage([""])),
                        Entry(("bar",), PatternMessage(["Bar"])),
                    ],
                )
            ],
        )
        assert "".join(ini_serialize(res)) == dedent(
            """\
            [Strings]
            foo=
            bar=Bar
            """
        )

    def test_empty_file(self):
        empty = Resource(Format.ini, [])
        assert ini_parse("") == empty
        assert ini_parse("\n") == empty
        assert ini_parse("\n\n") == empty
        assert ini_parse(" \n\n") == empty
        assert "".join(ini_serialize(empty)) == ""
