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

from importlib.resources import files
from textwrap import dedent
from unittest import TestCase

from moz.l10n.resource.data import Comment, Entry, Resource, Section
from moz.l10n.resource.inc import inc_parse, inc_serialize

# Show full diff in self.assertEqual. https://stackoverflow.com/a/61345284
# __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

source = files("tests.data").joinpath("defines.inc").read_bytes().decode("utf-8")


class TestInc(TestCase):
    def test_parse(self):
        res = inc_parse(source)
        self.assertEqual(
            res,
            Resource(
                [
                    Section(
                        [],
                        [
                            Comment("#filter emptyLines"),
                            Entry(["MOZ_LANGPACK_CREATOR"], "SeaMonkey e.V."),
                            Comment(
                                "If non-English locales wish to credit multiple contributors, uncomment this\n"
                                "variable definition and use the format specified.\n"
                                "# #define MOZ_LANGPACK_CONTRIBUTORS <em:contributor>Joe Solon</em:contributor> <em:contributor>Suzy Solon</em:contributor>"
                            ),
                            Entry(
                                ["seamonkey"],
                                "SeaMonkey",
                                comment="LOCALIZATION NOTE (seamonkey):\n"
                                "link title for https://www.seamonkey-project.org/ (in the personal toolbar)",
                            ),
                            Comment("#unfilter emptyLines"),
                        ],
                    )
                ],
            ),
        )

    def test_serialize(self):
        res = inc_parse(source)
        self.assertEqual(
            "".join(inc_serialize(res)),
            dedent(
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
            ),
        )

    def test_trim_comments(self):
        res = inc_parse(source)
        self.assertEqual(
            "".join(inc_serialize(res, trim_comments=True)),
            dedent(
                """\
                #filter emptyLines

                #define MOZ_LANGPACK_CREATOR SeaMonkey e.V.


                #define seamonkey SeaMonkey

                #unfilter emptyLines\n\n"""
            ),
        )
