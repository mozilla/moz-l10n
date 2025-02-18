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

from importlib_resources import files
from textwrap import dedent
from unittest import TestCase

from moz.l10n.formats import Format
from moz.l10n.formats.inc import inc_parse, inc_serialize
from moz.l10n.model import Comment, Entry, PatternMessage, Resource, Section

source = (
    files("tests.formats.data").joinpath("defines.inc").read_bytes().decode("utf-8")
)


class TestInc(TestCase):
    def test_parse(self):
        res = inc_parse(source)
        assert res == Resource(
            Format.inc,
            [
                Section(
                    (),
                    [
                        Comment("#filter emptyLines"),
                        Entry(
                            ("MOZ_LANGPACK_CREATOR",),
                            PatternMessage(["SeaMonkey e.V."]),
                        ),
                        Comment(
                            "If non-English locales wish to credit multiple contributors, uncomment this\n"
                            "variable definition and use the format specified.\n"
                            "# #define MOZ_LANGPACK_CONTRIBUTORS <em:contributor>Joe Solon</em:contributor> <em:contributor>Suzy Solon</em:contributor>"
                        ),
                        Entry(
                            ("seamonkey",),
                            PatternMessage(["SeaMonkey"]),
                            comment="LOCALIZATION NOTE (seamonkey):\n"
                            "link title for https://www.seamonkey-project.org/ (in the personal toolbar)",
                        ),
                        Comment("#unfilter emptyLines"),
                    ],
                )
            ],
        )

    def test_serialize(self):
        res = inc_parse(source)
        assert "".join(inc_serialize(res)) == dedent(
            """\
            #filter emptyLines

            #define MOZ_LANGPACK_CREATOR SeaMonkey e.V.

            # If non-English locales wish to credit multiple contributors, uncomment this
            # variable definition and use the format specified.
            # #define MOZ_LANGPACK_CONTRIBUTORS <em:contributor>Joe Solon</em:contributor> <em:contributor>Suzy Solon</em:contributor>

            # LOCALIZATION NOTE (seamonkey):
            # link title for https://www.seamonkey-project.org/ (in the personal toolbar)
            #define seamonkey SeaMonkey

            #unfilter emptyLines\n\n"""
        )

    def test_trim_comments(self):
        res = inc_parse(source)
        assert "".join(inc_serialize(res, trim_comments=True)) == dedent(
            """\
            #filter emptyLines

            #define MOZ_LANGPACK_CREATOR SeaMonkey e.V.


            #define seamonkey SeaMonkey

            #unfilter emptyLines\n\n"""
        )
