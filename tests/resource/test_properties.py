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

from moz.l10n.message import PatternMessage
from moz.l10n.resource.data import Entry, Resource, Section
from moz.l10n.resource.format import Format
from moz.l10n.resource.properties import properties_parse, properties_serialize


class TestProperties(TestCase):
    def test_backslashes(self):
        src = r"""one_line = This is one line
two_line = This is the first \
of two lines
one_line_trailing = This line has a \\ and ends in \\
two_lines_triple = This line is one of two and ends in \\\
and still has another line coming
"""
        res = properties_parse(src)
        self.assertEqual(
            res,
            Resource(
                Format.properties,
                [
                    Section(
                        [],
                        [
                            Entry(["one_line"], PatternMessage(["This is one line"])),
                            Entry(
                                ["two_line"],
                                PatternMessage(["This is the first of two lines"]),
                            ),
                            Entry(
                                ["one_line_trailing"],
                                PatternMessage(["This line has a \\ and ends in \\"]),
                            ),
                            Entry(
                                ["two_lines_triple"],
                                PatternMessage(
                                    [
                                        "This line is one of two and ends in \\and still has another line coming"
                                    ]
                                ),
                            ),
                        ],
                    )
                ],
            ),
        )
        self.assertEqual(
            "".join(properties_serialize(res)),
            r"""one_line = This is one line
two_line = This is the first of two lines
one_line_trailing = This line has a \\ and ends in \\
two_lines_triple = This line is one of two and ends in \\and still has another line coming
""",
        )

    def test_whitespace(self):
        # port of netwerk/test/PropertiesTest.cpp
        bytes = files("tests.resource.data").joinpath("test.properties").read_bytes()
        res = properties_parse(bytes)
        cc0 = (
            "Any copyright is dedicated to the Public Domain.\n"
            "http://creativecommons.org/publicdomain/zero/1.0/"
        )
        self.assertEqual(
            res,
            Resource(
                Format.properties,
                [
                    Section(
                        [],
                        [
                            Entry(["1"], PatternMessage(["1"]), comment=cc0),
                            Entry(["2"], PatternMessage(["2"])),
                            Entry(["3"], PatternMessage(["3"])),
                            Entry(["4"], PatternMessage(["4"])),
                            Entry(["5"], PatternMessage(["5"])),
                            Entry(["6"], PatternMessage(["6"])),
                            Entry(["7"], PatternMessage(["7 "])),
                            Entry(["8"], PatternMessage(["8 "])),
                            Entry(
                                ["9"],
                                PatternMessage(
                                    [
                                        "this is the first part of a continued line and here is the 2nd part"
                                    ]
                                ),
                                comment="this is a comment",
                            ),
                        ],
                    )
                ],
            ),
        )
        self.assertEqual(
            "".join(properties_serialize(res)),
            dedent(
                """\
                # Any copyright is dedicated to the Public Domain.
                # http://creativecommons.org/publicdomain/zero/1.0/
                1 = 1
                2 = 2
                3 = 3
                4 = 4
                5 = 5
                6 = 6
                7 = 7\\u0020
                8 = 8\\u0020
                # this is a comment
                9 = this is the first part of a continued line and here is the 2nd part
                """
            ),
        )
        self.assertEqual(
            "".join(properties_serialize(res, trim_comments=True)),
            dedent(
                """\
                1 = 1
                2 = 2
                3 = 3
                4 = 4
                5 = 5
                6 = 6
                7 = 7\\u0020
                8 = 8\\u0020
                9 = this is the first part of a continued line and here is the 2nd part
                """
            ),
        )

    def test_bug121341(self):
        # port of xpcom/tests/unit/test_bug121341.js
        bytes = (
            files("tests.resource.data").joinpath("bug121341.properties").read_bytes()
        )
        res = properties_parse(bytes)
        self.maxDiff = 10000
        self.assertEqual(
            res,
            Resource(
                Format.properties,
                [
                    Section(
                        [],
                        [
                            Entry(
                                ["1"], PatternMessage(["abc"]), comment="simple check"
                            ),
                            Entry(
                                ["2"],
                                PatternMessage(["xy\t"]),
                                comment="test whitespace trimming in key and value",
                            ),
                            Entry(
                                ["3"],
                                PatternMessage(["\u1234\t\r\n\u00AB\\u0001\n"]),
                                comment="test parsing of escaped values",
                            ),
                            Entry(
                                ["4"],
                                PatternMessage(["this is multiline property"]),
                                comment="test multiline properties",
                            ),
                            Entry(
                                ["5"],
                                PatternMessage(["this is another multiline property"]),
                                comment="",
                            ),
                            Entry(
                                ["6"],
                                PatternMessage(["test\u0036"]),
                                comment="property with DOS EOL",
                            ),
                            Entry(
                                ["7"],
                                PatternMessage(["yet another multiline propery"]),
                                comment="test multiline property with with DOS EOL",
                            ),
                            Entry(
                                ["8"],
                                PatternMessage(["\ttest5 \t"]),
                                comment="trimming should not trim escaped whitespaces",
                            ),
                            Entry(
                                ["9"],
                                PatternMessage([" test6\t\t    "]),
                                comment="another variant of #8",
                            ),
                            Entry(
                                ["10aሴb"],
                                PatternMessage(["c\uCDEFd"]),
                                comment="test UTF-8 encoded property/value",
                            ),
                            Entry(
                                ["11"],
                                PatternMessage(["\uABCD"]),
                                comment="next property should test unicode escaping at the boundary of parsing buffer\n"
                                + "buffer size is expected to be 4096 so add comments to get to this offset\n"
                                + (("#" * 79 + "\n") * 41)
                                + ("#" * 78),
                            ),
                        ],
                    )
                ],
            ),
        )
        assert (
            "".join(properties_serialize(res))
            == dedent(
                """\
                # simple check
                1 = abc
                # test whitespace trimming in key and value
                2 = xy\\t
                # test parsing of escaped values
                3 = \u1234\\t\\r\\n\u00AB\\\\u0001\\n
                # test multiline properties
                4 = this is multiline property
                5 = this is another multiline property
                # property with DOS EOL
                6 = test\u0036
                # test multiline property with with DOS EOL
                7 = yet another multiline propery
                # trimming should not trim escaped whitespaces
                8 = \\ttest5 \\t
                # another variant of #8
                9 = \\ test6\\t\\t   \\u0020
                # test UTF-8 encoded property/value
                10aሴb = c\uCDEFd
                # next property should test unicode escaping at the boundary of parsing buffer
                # buffer size is expected to be 4096 so add comments to get to this offset
                """
            )
            + ("#" * 80 + "\n") * 41
            + ("#" * 79 + "\n")
            + "11 = \uABCD\n"
        )

    def test_comment_in_multi(self):
        src = dedent(
            """\
            bar=one line with a \\
            # part that looks like a comment \\
            and an end
            """
        )
        res = properties_parse(src)
        exp = PatternMessage(
            ["one line with a # part that looks like a comment and an end"]
        )
        self.assertEqual(
            res, Resource(Format.properties, [Section([], [Entry(["bar"], exp)])])
        )
        self.assertEqual(
            "".join(properties_serialize(res)),
            "bar = one line with a # part that looks like a comment and an end\n",
        )

    def test_license_header(self):
        src = dedent(
            """\
            # Any copyright is dedicated to the Public Domain.
            # http://creativecommons.org/publicdomain/zero/1.0/

            foo = value
            """
        )
        res = properties_parse(src)
        self.assertEqual(
            res,
            Resource(
                Format.properties,
                [Section([], [Entry(["foo"], PatternMessage(["value"]))])],
                comment=dedent(
                    """\
                    Any copyright is dedicated to the Public Domain.
                    http://creativecommons.org/publicdomain/zero/1.0/"""
                ),
            ),
        )
        self.assertEqual("".join(properties_serialize(res)), src)
        self.assertEqual(
            "".join(properties_serialize(res, trim_comments=True)), "foo = value\n"
        )
