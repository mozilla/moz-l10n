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

from moz.l10n.android import android_parse, android_serialize
from moz.l10n.message import (
    CatchallKey,
    Expression,
    FunctionAnnotation,
    Markup,
    PatternMessage,
    SelectMessage,
    VariableRef,
)
from moz.l10n.resource import Comment, Entry, Metadata, Resource, Section

# Show full diff in self.assertEqual. https://stackoverflow.com/a/61345284
# __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

source = files("tests.data").joinpath("strings.xml").read_bytes()


class TestAndroid(TestCase):
    def test_parse(self):
        res = android_parse(source)
        self.assertEqual(
            res,
            Resource(
                [
                    Section(
                        ["!ENTITY"],
                        [
                            Entry(["foo"], PatternMessage(["Foo"])),
                            Entry(
                                ["bar"],
                                PatternMessage(
                                    [
                                        "Bar ",
                                        Expression(
                                            VariableRef("foo"),
                                            FunctionAnnotation("entity"),
                                        ),
                                    ]
                                ),
                            ),
                        ],
                    ),
                    Section(
                        [],
                        [
                            Entry(["one"], PatternMessage([])),
                            Entry(["two"], PatternMessage([])),
                            Entry(["three"], PatternMessage(["value"]), comment="bar"),
                            Entry(
                                ["four"],
                                PatternMessage(["multi-line comment"]),
                                comment="bar\n\nfoo",
                                meta=[Metadata("translatable", "false")],
                            ),
                            Comment("standalone"),
                            Entry(
                                ["welcome"],
                                PatternMessage(
                                    [
                                        "Welcome to ",
                                        Markup("open", "b"),
                                        Expression(
                                            VariableRef("foo"),
                                            FunctionAnnotation("entity"),
                                        ),
                                        Markup("close", "b"),
                                        "!",
                                    ]
                                ),
                            ),
                            Entry(
                                ["placeholders"],
                                PatternMessage(
                                    [
                                        "Hello, ",
                                        Expression(
                                            VariableRef("%1$s"),
                                            FunctionAnnotation("string"),
                                        ),
                                        "! You have ",
                                        Expression(
                                            VariableRef("%2$d"),
                                            FunctionAnnotation("integer"),
                                        ),
                                        " new messages.",
                                    ]
                                ),
                            ),
                            Entry(
                                ["escape_html"],
                                PatternMessage(
                                    [
                                        "Hello, ",
                                        Expression(
                                            VariableRef("%1$s"),
                                            FunctionAnnotation("string"),
                                        ),
                                        "! You have ",
                                        Expression("<b>", FunctionAnnotation("html")),
                                        Expression(
                                            VariableRef("%2$d"),
                                            FunctionAnnotation("integer"),
                                        ),
                                        " new messages",
                                        Expression("</b>", FunctionAnnotation("html")),
                                        ".",
                                    ]
                                ),
                            ),
                            Entry(["ws_trimmed"], PatternMessage([" "])),
                            Entry(
                                ["ws_quoted"], PatternMessage([" \u0020 \u2008 \u2003"])
                            ),
                            Entry(
                                ["ws_escaped"],
                                PatternMessage([" \u0020 \u2008 \u2003"]),
                            ),
                            Entry(["control_chars"], PatternMessage(["\u0000 \u0001"])),
                            Entry(
                                ["foo"],
                                PatternMessage(
                                    [
                                        'Foo Bar <a href="foo?id=',
                                        Expression(
                                            VariableRef("%s"),
                                            FunctionAnnotation("string"),
                                        ),
                                        '">baz',
                                        Expression("</a>", FunctionAnnotation("html")),
                                        " is cool",
                                    ]
                                ),
                            ),
                            Entry(
                                ["busy"],
                                PatternMessage(
                                    [
                                        "Sorry, ",
                                        Expression(
                                            VariableRef("foo"),
                                            FunctionAnnotation("entity"),
                                        ),
                                        " is ",
                                        Expression("<i>", FunctionAnnotation("html")),
                                        "not available",
                                        Expression("</i>", FunctionAnnotation("html")),
                                        " just now.",
                                    ]
                                ),
                            ),
                            Entry(["planets_array", "0"], PatternMessage(["Mercury"])),
                            Entry(["planets_array", "1"], PatternMessage(["Venus"])),
                            Entry(["planets_array", "2"], PatternMessage(["Earth"])),
                            Entry(["planets_array", "3"], PatternMessage(["Mars"])),
                            Entry(
                                ["numberOfSongsAvailable"],
                                SelectMessage(
                                    [
                                        Expression(
                                            VariableRef("quantity"),
                                            FunctionAnnotation("number"),
                                        )
                                    ],
                                    {
                                        ("one",): [
                                            Expression(
                                                VariableRef("%d"),
                                                FunctionAnnotation("integer"),
                                            ),
                                            " song found.",
                                        ],
                                        (CatchallKey("other"),): [
                                            Expression(
                                                VariableRef("%d"),
                                                FunctionAnnotation("integer"),
                                            ),
                                            " songs found.",
                                        ],
                                    },
                                ),
                                comment=dedent(
                                    """\
                                    As a developer, you should always supply "one" and "other"
                                    strings. Your translators will know which strings are actually
                                    needed for their language. Always include %d in "one" because
                                    translators will need to use %d for languages where "one"
                                    doesn't mean 1 (as explained above)."""
                                ),
                            ),
                            Entry(
                                ["numberOfSongsAvailable_pl"],
                                SelectMessage(
                                    [
                                        Expression(
                                            VariableRef("quantity"),
                                            FunctionAnnotation("number"),
                                        )
                                    ],
                                    {
                                        ("one",): [
                                            "Znaleziono ",
                                            Expression(
                                                VariableRef("%d"),
                                                FunctionAnnotation("integer"),
                                            ),
                                            " piosenkę.",
                                        ],
                                        ("few",): [
                                            "Znaleziono ",
                                            Expression(
                                                VariableRef("%d"),
                                                FunctionAnnotation("integer"),
                                            ),
                                            " piosenki.",
                                        ],
                                        (CatchallKey("other"),): [
                                            "Znaleziono ",
                                            Expression(
                                                VariableRef("%d"),
                                                FunctionAnnotation("integer"),
                                            ),
                                            " piosenek.",
                                        ],
                                    },
                                ),
                            ),
                        ],
                    ),
                ],
                comment="Test translation file.\n"
                "Any copyright is dedicated to the Public Domain.\n"
                "http://creativecommons.org/publicdomain/zero/1.0/",
            ),
        )

    def test_serialize(self):
        res = android_parse(source)
        self.assertEqual(
            "".join(android_serialize(res)),
            dedent(
                """\
                <?xml version="1.0" encoding="utf-8"?>

                <!--
                  Test translation file.
                  Any copyright is dedicated to the Public Domain.
                  http://creativecommons.org/publicdomain/zero/1.0/
                -->

                <!DOCTYPE resources [
                  <!ENTITY foo "Foo">
                  <!ENTITY bar "Bar &foo;">
                ]>
                <resources>
                  <string name="one"></string>
                  <string name="two"></string>
                  <!-- bar -->
                  <string name="three">value</string>
                  <!--
                    bar

                    foo
                  -->
                  <string name="four" translatable="false">multi-line comment</string>
                  <!-- standalone -->

                  <string name="welcome">Welcome to <b>&foo;</b>!</string>
                  <string name="placeholders">Hello, %1$s! You have %2$d new messages.</string>
                  <string name="escape_html">Hello, %1$s! You have &lt;b&gt;%2$d new messages&lt;/b&gt;.</string>
                  <string name="ws_trimmed"> </string>
                  <string name="ws_quoted">"   \\u8200 \\u8195"</string>
                  <string name="ws_escaped">"   \\u8200 \\u8195"</string>
                  <string name="control_chars">\\u0000 \\u0001</string>
                  <string name="foo">Foo Bar &lt;a href=\\"foo\\?id=%s\\"&gt;baz&lt;/a&gt; is cool</string>
                  <string name="busy">Sorry, &foo; is &lt;i&gt;not available&lt;/i&gt; just now.</string>
                  <string-array name="planets_array">
                    <item>Mercury</item>
                    <item>Venus</item>
                    <item>Earth</item>
                    <item>Mars</item>
                  </string-array>
                  <plurals name="numberOfSongsAvailable">
                    <!--
                      As a developer, you should always supply "one" and "other"
                      strings. Your translators will know which strings are actually
                      needed for their language. Always include %d in "one" because
                      translators will need to use %d for languages where "one"
                      doesn't mean 1 (as explained above).
                    -->
                    <item quantity="one">%d song found.</item>
                    <item quantity="other">%d songs found.</item>
                  </plurals>
                  <plurals name="numberOfSongsAvailable_pl">
                    <item quantity="one">Znaleziono %d piosenkę.</item>
                    <item quantity="few">Znaleziono %d piosenki.</item>
                    <item quantity="other">Znaleziono %d piosenek.</item>
                  </plurals>
                </resources>
                """
            ),
        )

    def test_trim_comments(self):
        res = android_parse(source)
        self.assertEqual(
            "".join(android_serialize(res, trim_comments=True)),
            dedent(
                """\
                <?xml version="1.0" encoding="utf-8"?>
                <!DOCTYPE resources [
                  <!ENTITY foo "Foo">
                  <!ENTITY bar "Bar &foo;">
                ]>
                <resources>
                  <string name="one"></string>
                  <string name="two"></string>
                  <string name="three">value</string>
                  <string name="four" translatable="false">multi-line comment</string>
                  <string name="welcome">Welcome to <b>&foo;</b>!</string>
                  <string name="placeholders">Hello, %1$s! You have %2$d new messages.</string>
                  <string name="escape_html">Hello, %1$s! You have &lt;b&gt;%2$d new messages&lt;/b&gt;.</string>
                  <string name="ws_trimmed"> </string>
                  <string name="ws_quoted">"   \\u8200 \\u8195"</string>
                  <string name="ws_escaped">"   \\u8200 \\u8195"</string>
                  <string name="control_chars">\\u0000 \\u0001</string>
                  <string name="foo">Foo Bar &lt;a href=\\"foo\\?id=%s\\"&gt;baz&lt;/a&gt; is cool</string>
                  <string name="busy">Sorry, &foo; is &lt;i&gt;not available&lt;/i&gt; just now.</string>
                  <string-array name="planets_array">
                    <item>Mercury</item>
                    <item>Venus</item>
                    <item>Earth</item>
                    <item>Mars</item>
                  </string-array>
                  <plurals name="numberOfSongsAvailable">
                    <item quantity="one">%d song found.</item>
                    <item quantity="other">%d songs found.</item>
                  </plurals>
                  <plurals name="numberOfSongsAvailable_pl">
                    <item quantity="one">Znaleziono %d piosenkę.</item>
                    <item quantity="few">Znaleziono %d piosenki.</item>
                    <item quantity="other">Znaleziono %d piosenek.</item>
                  </plurals>
                </resources>
                """
            ),
        )

    def test_idempotent(self):
        res1 = android_parse(source)
        src_res = "".join(android_serialize(res1))
        res2 = android_parse(src_res)
        self.assertEqual(res1, res2)
