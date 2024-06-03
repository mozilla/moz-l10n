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

from moz.l10n.message import (
    CatchallKey,
    Expression,
    FunctionAnnotation,
    Markup,
    PatternMessage,
    SelectMessage,
    VariableRef,
)
from moz.l10n.resource.android import android_parse, android_serialize
from moz.l10n.resource.data import Comment, Entry, Metadata, Resource, Section
from moz.l10n.resource.format import Format

# Show full diff in self.assertEqual. https://stackoverflow.com/a/61345284
# __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

source = files("tests.resource.data").joinpath("strings.xml").read_bytes()


class TestAndroid(TestCase):
    def test_parse(self):
        res = android_parse(source)
        assert res == Resource(
            Format.android,
            comment="Test translation file.\n"
            "Any copyright is dedicated to the Public Domain.\n"
            "http://creativecommons.org/publicdomain/zero/1.0/",
            meta=[Metadata("xmlns:xliff", "urn:oasis:names:tc:xliff:document:1.2")],
            sections=[
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
                        ),
                        Entry(
                            ["five"],
                            PatternMessage(
                                [
                                    Expression(
                                        "@string/three",
                                        FunctionAnnotation("reference"),
                                    )
                                ]
                            ),
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
                                        VariableRef("arg1"),
                                        FunctionAnnotation("string"),
                                        {"source": "%1$s"},
                                    ),
                                    "! You have ",
                                    Expression(
                                        VariableRef("arg2"),
                                        FunctionAnnotation("integer"),
                                        {"source": "%2$d"},
                                    ),
                                    " new messages.",
                                ]
                            ),
                        ),
                        Entry(
                            ["real_html"],
                            PatternMessage(
                                [
                                    "Hello, ",
                                    Expression(
                                        VariableRef("arg1"),
                                        FunctionAnnotation("string"),
                                        {"source": "%1$s"},
                                    ),
                                    "! You have ",
                                    Markup("open", "b"),
                                    Expression(
                                        VariableRef("arg2"),
                                        FunctionAnnotation("integer"),
                                        {"source": "%2$d"},
                                    ),
                                    " new messages",
                                    Markup("close", "b"),
                                    ".",
                                ]
                            ),
                        ),
                        Entry(
                            ["escaped_html"],
                            PatternMessage(
                                [
                                    "Hello, ",
                                    Expression(
                                        VariableRef("arg1"),
                                        FunctionAnnotation("string"),
                                        {"source": "%1$s"},
                                    ),
                                    "! You have ",
                                    Expression("<b>", FunctionAnnotation("html")),
                                    Expression(
                                        VariableRef("arg2"),
                                        FunctionAnnotation("integer"),
                                        {"source": "%2$d"},
                                    ),
                                    " new messages",
                                    Expression("</b>", FunctionAnnotation("html")),
                                    ".",
                                ]
                            ),
                        ),
                        Entry(
                            ["protected"],
                            PatternMessage(
                                [
                                    "Hello, ",
                                    Expression(
                                        VariableRef("user"),
                                        FunctionAnnotation(
                                            "xliff:g", {"id": "user", "example": "Bob"}
                                        ),
                                        {"translate": "no", "source": "%1$s"},
                                    ),
                                    "! You have ",
                                    Expression(
                                        VariableRef("count"),
                                        FunctionAnnotation("xliff:g", {"id": "count"}),
                                        {"translate": "no", "source": "%2$d"},
                                    ),
                                    " new messages.",
                                ]
                            ),
                        ),
                        Entry(
                            ["nested_protections"],
                            PatternMessage(
                                [
                                    "Welcome to ",
                                    Markup(
                                        "open",
                                        "xliff:g",
                                        attributes={"translate": "no"},
                                    ),
                                    Markup("open", "b"),
                                    Expression("Foo", None, {"translate": "no"}),
                                    Markup("close", "b"),
                                    "!",
                                    Markup(
                                        "close",
                                        "xliff:g",
                                        attributes={"translate": "no"},
                                    ),
                                ]
                            ),
                        ),
                        Entry(["ws_trimmed"], PatternMessage([" "])),
                        Entry(["ws_quoted"], PatternMessage([" \u0020 \u2008 \u2003"])),
                        Entry(
                            ["ws_escaped"],
                            PatternMessage([" \u0020 \u2008 \u2003"]),
                        ),
                        Entry(
                            ["ws_with_entities"],
                            PatternMessage(
                                [
                                    " one ",
                                    Expression(
                                        VariableRef("foo"),
                                        FunctionAnnotation("entity"),
                                        {"translate": "no"},
                                    ),
                                    Expression(" two ", attributes={"translate": "no"}),
                                    Expression(
                                        VariableRef("bar"),
                                        FunctionAnnotation("entity"),
                                        {"translate": "no"},
                                    ),
                                    " three ",
                                ]
                            ),
                        ),
                        Entry(
                            ["ws_with_html"],
                            PatternMessage(
                                [
                                    " one",
                                    Markup("open", "b"),
                                    " two ",
                                    Markup("close", "b"),
                                    "three ",
                                ]
                            ),
                        ),
                        Entry(["control_chars"], PatternMessage(["\u0000 \u0001"])),
                        Entry(
                            ["percent"],
                            PatternMessage(
                                [Expression("%", attributes={"source": "%%"})]
                            ),
                        ),
                        Entry(["single_quote"], PatternMessage(["They're great"])),
                        Entry(["double_quotes"], PatternMessage(['They are "great"'])),
                        Entry(
                            ["both_quotes"],
                            PatternMessage(['They\'re really "great"']),
                        ),
                        Entry(
                            ["foo"],
                            PatternMessage(
                                [
                                    'Foo Bar <a href="foo?id=',
                                    Expression(
                                        VariableRef("arg"),
                                        FunctionAnnotation("string"),
                                        {"source": "%s"},
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
                                            VariableRef("arg"),
                                            FunctionAnnotation("integer"),
                                            {"source": "%d"},
                                        ),
                                        " song found.",
                                    ],
                                    (CatchallKey("other"),): [
                                        Expression(
                                            VariableRef("arg"),
                                            FunctionAnnotation("integer"),
                                            {"source": "%d"},
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
                                    doesn't mean 1."""
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
                                            VariableRef("arg"),
                                            FunctionAnnotation("integer"),
                                            {"source": "%d"},
                                        ),
                                        " piosenkę.",
                                    ],
                                    ("few",): [
                                        "Znaleziono ",
                                        Expression(
                                            VariableRef("arg"),
                                            FunctionAnnotation("integer"),
                                            {"source": "%d"},
                                        ),
                                        " piosenki.",
                                    ],
                                    (CatchallKey("other"),): [
                                        "Znaleziono ",
                                        Expression(
                                            VariableRef("arg"),
                                            FunctionAnnotation("integer"),
                                            {"source": "%d"},
                                        ),
                                        " piosenek.",
                                    ],
                                },
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_serialize(self):
        res = android_parse(source)
        ser = "".join(android_serialize(res))
        assert ser == dedent(
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
            <resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">
              <string name="one"></string>
              <string name="two"></string>
              <!-- bar -->
              <string name="three">value</string>
              <!--
                bar

                foo
              -->
              <string name="four">multi-line comment</string>
              <string name="five" translatable="false">@string/three</string>
              <!-- standalone -->

              <string name="welcome">Welcome to <b>&foo;</b>!</string>
              <string name="placeholders">Hello, %1$s! You have %2$d new messages.</string>
              <string name="real_html">Hello, %1$s! You have <b>%2$d new messages</b>.</string>
              <string name="escaped_html">Hello, %1$s! You have &lt;b&gt;%2$d new messages&lt;/b&gt;.</string>
              <string name="protected">Hello, <xliff:g id="user" example="Bob">%1$s</xliff:g>! You have <xliff:g id="count">%2$d</xliff:g> new messages.</string>
              <string name="nested_protections">Welcome to <xliff:g><b><xliff:g>Foo</xliff:g></b>!</xliff:g></string>
              <string name="ws_trimmed">" "</string>
              <string name="ws_quoted">"   \\u8200 \\u8195"</string>
              <string name="ws_escaped">"   \\u8200 \\u8195"</string>
              <string name="ws_with_entities">" one "<xliff:g>&foo;</xliff:g><xliff:g> two </xliff:g><xliff:g>&bar;</xliff:g>" three "</string>
              <string name="ws_with_html">" one"<b> two </b>"three "</string>
              <string name="control_chars">\\u0000 \\u0001</string>
              <string name="percent">%%</string>
              <string name="single_quote">They\\'re great</string>
              <string name="double_quotes">They are \\"great\\"</string>
              <string name="both_quotes">They\\'re really \\"great\\"</string>
              <string name="foo">Foo Bar &lt;a href=\\"foo?id=%s\\"&gt;baz&lt;/a&gt; is cool</string>
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
                  doesn't mean 1.
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
        )

    def test_trim_comments(self):
        res = android_parse(source)
        ser = "".join(android_serialize(res, trim_comments=True))
        assert ser == dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <!DOCTYPE resources [
              <!ENTITY foo "Foo">
              <!ENTITY bar "Bar &foo;">
            ]>
            <resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">
              <string name="one"></string>
              <string name="two"></string>
              <string name="three">value</string>
              <string name="four">multi-line comment</string>
              <string name="five" translatable="false">@string/three</string>
              <string name="welcome">Welcome to <b>&foo;</b>!</string>
              <string name="placeholders">Hello, %1$s! You have %2$d new messages.</string>
              <string name="real_html">Hello, %1$s! You have <b>%2$d new messages</b>.</string>
              <string name="escaped_html">Hello, %1$s! You have &lt;b&gt;%2$d new messages&lt;/b&gt;.</string>
              <string name="protected">Hello, <xliff:g id="user" example="Bob">%1$s</xliff:g>! You have <xliff:g id="count">%2$d</xliff:g> new messages.</string>
              <string name="nested_protections">Welcome to <xliff:g><b><xliff:g>Foo</xliff:g></b>!</xliff:g></string>
              <string name="ws_trimmed">" "</string>
              <string name="ws_quoted">"   \\u8200 \\u8195"</string>
              <string name="ws_escaped">"   \\u8200 \\u8195"</string>
              <string name="ws_with_entities">" one "<xliff:g>&foo;</xliff:g><xliff:g> two </xliff:g><xliff:g>&bar;</xliff:g>" three "</string>
              <string name="ws_with_html">" one"<b> two </b>"three "</string>
              <string name="control_chars">\\u0000 \\u0001</string>
              <string name="percent">%%</string>
              <string name="single_quote">They\\'re great</string>
              <string name="double_quotes">They are \\"great\\"</string>
              <string name="both_quotes">They\\'re really \\"great\\"</string>
              <string name="foo">Foo Bar &lt;a href=\\"foo?id=%s\\"&gt;baz&lt;/a&gt; is cool</string>
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
        )

    def test_idempotent(self):
        res1 = android_parse(source)
        src_res = "".join(android_serialize(res1))
        res2 = android_parse(src_res)
        self.assertEqual(res1, res2)

    def test_xliff_xmlns(self):
        exp = Expression(" X ", FunctionAnnotation("foo", {"opt": "OPT"}))
        res = Resource(
            Format.android, [Section([], [Entry(["x"], PatternMessage([exp]))])]
        )

        ser = "".join(android_serialize(res, trim_comments=True))
        assert ser == dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <resources>
              <string name="x">" X "</string>
            </resources>
            """
        )

        exp.attributes["translate"] = "no"
        ser = "".join(android_serialize(res, trim_comments=True))
        assert ser == dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">
              <string name="x"><xliff:g opt="OPT"> X </xliff:g></string>
            </resources>
            """
        )

    def test_translate_no(self):
        msg = PatternMessage(
            [
                Markup("open", "x", attributes={"translate": "no"}),
                "Foo",
                Markup("close", "x", attributes={"translate": "no"}),
            ]
        )
        res = Resource(Format.android, [Section([], [Entry(["x"], msg)])])

        ser = "".join(android_serialize(res, trim_comments=True))
        assert ser == dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">
              <string name="x"><xliff:g>Foo</xliff:g></string>
            </resources>
            """
        )
