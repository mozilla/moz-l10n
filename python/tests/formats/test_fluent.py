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

from moz.l10n.formats import Format
from moz.l10n.formats.fluent import (
    fluent_parse,
    fluent_parse_entry,
    fluent_parse_message,
    fluent_serialize,
    fluent_serialize_message,
)
from moz.l10n.model import (
    CatchallKey,
    Comment,
    Entry,
    Expression,
    LinePos,
    Metadata,
    PatternMessage,
    Resource,
    Section,
    SelectMessage,
    VariableRef,
)

from . import get_linepos, get_test_resource


class TestFluent(TestCase):
    def test_equality_same(self):
        source = 'progress = Progress: { NUMBER($num, style: "percent") }.'
        res1 = fluent_parse(source)
        res2 = fluent_parse(source)
        assert res1 == res2

    def test_equality_different_whitespace(self):
        source1 = b"foo = { $arg }"
        source2 = b"foo = {    $arg    }"
        res1 = fluent_parse(source1)
        res2 = fluent_parse(source2)
        assert res1 == res2

    def test_number_selector(self):
        src = dedent(
            """\
            no-placeholder =
                { $num ->
                    [one] One
                   *[other] Other
                }
            has-placeholder =
                { $num ->
                    [one] One { $num }
                   *[other] Other
                }
            """
        )
        res = fluent_parse(src)
        other = CatchallKey("other")
        entries: list[Entry[SelectMessage] | Comment] = [
            Entry(
                ("no-placeholder",),
                SelectMessage(
                    declarations={"num": Expression(VariableRef("num"), "number")},
                    selectors=(VariableRef("num"),),
                    variants={
                        ("one",): ["One"],
                        (other,): ["Other"],
                    },
                ),
                linepos=LinePos(1, 1, 2, 6),
            ),
            Entry(
                ("has-placeholder",),
                SelectMessage(
                    declarations={"num_1": Expression(VariableRef("num"), "number")},
                    selectors=(VariableRef("num_1"),),
                    variants={
                        ("one",): ["One ", Expression(VariableRef("num"))],
                        (other,): ["Other"],
                    },
                ),
                linepos=LinePos(6, 6, 7, 11),
            ),
        ]
        assert res == Resource(Format.fluent, [Section((), entries)])
        assert "".join(fluent_serialize(res)) == src

    def test_parse_entries(self):
        source = "msg = body\n"
        entry = fluent_parse_entry(source, with_linepos=False)
        assert entry == Entry(("msg",), PatternMessage(["body"]))

        source = "-term = body\n  .attr = value\n"
        entry = fluent_parse_entry(source)
        assert entry == Entry(
            ("-term",),
            PatternMessage(["body"]),
            properties={"attr": PatternMessage(["value"])},
            linepos=get_linepos(1),
        )

        with self.assertRaises(ValueError):
            fluent_parse_entry("# comment\n")

    def test_messages(self):
        msg = fluent_parse_message("body")
        assert msg == PatternMessage(["body"])
        assert fluent_serialize_message(msg) == "body"

        msg = fluent_parse_message("hello { $x }")
        assert msg == PatternMessage(["hello ", Expression(VariableRef("x"))])
        assert fluent_serialize_message(msg) == "hello { $x }"

        msg = fluent_parse_message("1\n  2  \n3  \n")
        assert msg == PatternMessage(["1\n  2  \n3"])
        assert fluent_serialize_message(msg) == "1\n  2  \n3"

        msg = fluent_parse_message("# comment")
        assert msg == PatternMessage(["# comment"])
        assert fluent_serialize_message(msg) == "# comment"

        msg = fluent_parse_message(
            """
            { $num ->
                [one] One {$num}
               *[other] Other
            }
            """
        )
        assert msg == SelectMessage(
            declarations={"num_1": Expression(VariableRef("num"), function="number")},
            selectors=(VariableRef("num_1"),),
            variants={
                ("one",): ["One ", Expression(VariableRef("num"))],
                (CatchallKey("other"),): ["Other"],
            },
        )
        assert fluent_serialize_message(msg) == dedent(
            """\
            { $num ->
                [one] One { $num }
               *[other] Other
            }"""
        )

        with self.assertRaises(ValueError):
            fluent_parse_message("fail {")

    def test_empty_patterns(self):
        entries: list[Entry[PatternMessage] | Comment] = [
            Entry(("a",), PatternMessage([])),
            Entry(("b",), PatternMessage([""])),
            Entry(("c",), PatternMessage([]), {"x": PatternMessage([])}),
            Entry(("-d",), PatternMessage([]), {"x": PatternMessage([])}),
            Entry(("e",), PatternMessage([" "])),
            Entry(("f",), PatternMessage(["\n \t"])),
            Entry(("g",), PatternMessage([" x\n"])),
            Entry(("h",), PatternMessage(["x", " y ", "z"])),
        ]
        res = Resource(Format.fluent, [Section((), entries)])
        assert "".join(fluent_serialize(res)) == dedent(
            """\
            a = { "" }
            b = { "" }
            c =
                .x = { "" }
            -d = { "" }
                .x = { "" }
            e = { " " }
            f = { "\\u000A \\u0009" }
            g = { " " }x{ "\\u000A" }
            h = x y z
            """
        )

    def test_resource(self):
        res = fluent_parse(
            dedent(
                """\
                ### Resource Comment

                ## Group Comment

                simple = A

                # Standalone Comment

                ##

                # Message Comment
                # on two lines.
                expressions = A {$arg} B {msg.foo} C {-term(x:42)}
                functions = {NUMBER($arg)}{FOO("bar",opt:"val")}
                has-attr = ABC
                  .attr = Attr
                # Attr Comment
                has-only-attr =
                  .attr = Attr

                single-sel =
                  { $num ->
                      [one] One
                     *[other] Other
                  }
                two-sels =
                  pre { $a ->
                      [1] One
                     *[2] Two
                  } mid { $b ->
                     *[bb] BB
                      [cc] CC
                  } post
                deep-sels =
                  { $a ->
                      [0]
                        { $b ->
                            [one] {""}
                           *[other] 0,x
                        }
                      [one]
                        { $b ->
                            [one] {"1,1"}
                           *[other] 1,x
                        }
                     *[other]
                        { $b ->
                            [0] x,0
                            [one] x,1
                           *[other] x,x
                        }
                  }
                -term = Term
                  .attr = foo
                term-sel =
                  { -term.attr ->
                     [foo] Foo
                    *[other] Other
                  }
                """
            ),
        )
        other = CatchallKey("other")
        entries = [
            Entry(
                ("expressions",),
                PatternMessage(
                    [
                        "A ",
                        Expression(VariableRef("arg")),
                        " B ",
                        Expression("msg.foo", "message"),
                        " C ",
                        Expression("-term", "message", {"x": "42"}),
                    ]
                ),
                comment="Message Comment\non two lines.",
                linepos=get_linepos(11, 13),
            ),
            Entry(
                ("functions",),
                PatternMessage(
                    [
                        Expression(VariableRef("arg"), "number"),
                        Expression("bar", "foo", {"opt": "val"}),
                    ]
                ),
                linepos=get_linepos(14),
            ),
            Entry(
                ("has-attr",),
                PatternMessage(["ABC"]),
                properties={"attr": PatternMessage(["Attr"])},
                linepos=get_linepos(15),
            ),
            Entry(
                ("has-only-attr",),
                PatternMessage([]),
                properties={"attr": PatternMessage(["Attr"])},
                comment="Attr Comment",
                linepos=get_linepos(17, 19),
            ),
            Entry(
                ("single-sel",),
                SelectMessage(
                    declarations={"num": Expression(VariableRef("num"), "number")},
                    selectors=(VariableRef("num"),),
                    variants={
                        ("one",): ["One"],
                        (other,): ["Other"],
                    },
                ),
                linepos=LinePos(21, 21, 22, 26),
            ),
            Entry(
                ("two-sels",),
                SelectMessage(
                    declarations={
                        "a": Expression(VariableRef("a"), "number"),
                        "b": Expression(VariableRef("b"), "string"),
                    },
                    selectors=(VariableRef("a"), VariableRef("b")),
                    variants={
                        ("1", "cc"): ["pre One mid CC post"],
                        ("1", CatchallKey("bb")): ["pre One mid BB post"],
                        (CatchallKey("2"), "cc"): ["pre Two mid CC post"],
                        (CatchallKey("2"), CatchallKey("bb")): ["pre Two mid BB post"],
                    },
                ),
                linepos=LinePos(26, 26, 27, 34),
            ),
            Entry(
                ("deep-sels",),
                SelectMessage(
                    declarations={
                        "a": Expression(VariableRef("a"), "number"),
                        "b": Expression(VariableRef("b"), "number"),
                    },
                    selectors=(VariableRef("a"), VariableRef("b")),
                    variants={
                        ("0", "one"): [Expression("")],
                        ("0", other): ["0,x"],
                        ("one", "one"): [Expression("1,1")],
                        ("one", other): ["1,x"],
                        (other, "0"): ["x,0"],
                        (other, "one"): ["x,1"],
                        (other, other): ["x,x"],
                    },
                ),
                linepos=LinePos(34, 34, 35, 53),
            ),
            Entry(
                ("-term",),
                PatternMessage(["Term"]),
                properties={"attr": PatternMessage(["foo"])},
                linepos=get_linepos(53),
            ),
            Entry(
                ("term-sel",),
                SelectMessage(
                    declarations={"_1": Expression("-term.attr", "message")},
                    selectors=(VariableRef("_1"),),
                    variants={
                        ("foo",): ["Foo"],
                        (other,): ["Other"],
                    },
                ),
                linepos=LinePos(55, 55, 56, 60),
            ),
        ]
        assert res == Resource(
            Format.fluent,
            [
                Section(
                    id=(),
                    entries=[
                        Entry(
                            ("simple",),
                            PatternMessage(["A"]),
                            linepos=get_linepos(5),
                        ),
                        Comment("Standalone Comment"),
                    ],
                    comment="Group Comment",
                    linepos=get_linepos(3),
                ),
                Section((), entries, linepos=get_linepos(9)),
            ],
            comment="Resource Comment",
        )
        assert "".join(fluent_serialize(res)) == dedent(
            """\
            ### Resource Comment


            ## Group Comment

            simple = A

            # Standalone Comment


            ##

            # Message Comment
            # on two lines.
            expressions = A { $arg } B { msg.foo } C { -term(x: 42) }
            functions = { NUMBER($arg) }{ FOO("bar", opt: "val") }
            has-attr = ABC
                .attr = Attr
            # Attr Comment
            has-only-attr =
                .attr = Attr
            single-sel =
                { $num ->
                    [one] One
                   *[other] Other
                }
            two-sels =
                { $a ->
                    [1]
                        { $b ->
                            [cc] pre One mid CC post
                           *[bb] pre One mid BB post
                        }
                   *[2]
                        { $b ->
                            [cc] pre Two mid CC post
                           *[bb] pre Two mid BB post
                        }
                }
            deep-sels =
                { $a ->
                    [0]
                        { $b ->
                            [one] { "" }
                           *[other] 0,x
                        }
                    [one]
                        { $b ->
                            [one] { "1,1" }
                           *[other] 1,x
                        }
                   *[other]
                        { $b ->
                            [0] x,0
                            [one] x,1
                           *[other] x,x
                        }
                }
            -term = Term
                .attr = foo
            term-sel =
                { -term.attr ->
                    [foo] Foo
                   *[other] Other
                }
            """
        )
        assert "".join(fluent_serialize(res, trim_comments=True)) == dedent(
            """\
            simple = A
            expressions = A { $arg } B { msg.foo } C { -term(x: 42) }
            functions = { NUMBER($arg) }{ FOO("bar", opt: "val") }
            has-attr = ABC
                .attr = Attr
            has-only-attr =
                .attr = Attr
            single-sel =
                { $num ->
                    [one] One
                   *[other] Other
                }
            two-sels =
                { $a ->
                    [1]
                        { $b ->
                            [cc] pre One mid CC post
                           *[bb] pre One mid BB post
                        }
                   *[2]
                        { $b ->
                            [cc] pre Two mid CC post
                           *[bb] pre Two mid BB post
                        }
                }
            deep-sels =
                { $a ->
                    [0]
                        { $b ->
                            [one] { "" }
                           *[other] 0,x
                        }
                    [one]
                        { $b ->
                            [one] { "1,1" }
                           *[other] 1,x
                        }
                   *[other]
                        { $b ->
                            [0] x,0
                            [one] x,1
                           *[other] x,x
                        }
                }
            -term = Term
                .attr = foo
            term-sel =
                { -term.attr ->
                    [foo] Foo
                   *[other] Other
                }
                """
        )

    def test_escapes(self):
        source = 'key = { "" } { "\t" } { "\\u000a" }'
        res = fluent_parse(source)
        exp_msg = PatternMessage(
            [Expression(""), " ", Expression("\t"), " ", Expression("\n")]
        )
        assert res == Resource(
            Format.fluent,
            [
                Section(
                    id=(), entries=[Entry(("key",), exp_msg, linepos=get_linepos(1))]
                )
            ],
        )
        assert (
            "".join(fluent_serialize(res))
            == 'key = { "" } { "\\u0009" } { "\\u000A" }\n'
        )

    def test_comment(self):
        res = fluent_parse("msg = body\n  .attr = value")

        res.sections[0].entries[0].comment = "comment1"
        assert "".join(fluent_serialize(res)) == dedent(
            """\
            # comment1
            msg = body
                .attr = value
            """
        )
        assert (
            "".join(fluent_serialize(res, trim_comments=True))
            == "msg = body\n    .attr = value\n"
        )

    def test_meta(self):
        res = fluent_parse("one = foo\ntwo = bar")
        res.sections[0].entries[1].meta = [Metadata("a", "42"), Metadata("b", "False")]
        with self.assertRaises(ValueError) as ec:
            "".join(fluent_serialize(res))
        assert ec.exception.args == ("Metadata requires serialize_metadata parameter",)
        assert (
            "".join(fluent_serialize(res, lambda _: None)) == "one = foo\ntwo = bar\n"
        )
        assert "".join(
            fluent_serialize(res, lambda m: f"@{m.key}: {m.value}")
        ) == dedent(
            """\
            one = foo
            # @a: 42
            # @b: False
            two = bar
            """
        )
        assert (
            "".join(fluent_serialize(res, trim_comments=True))
            == "one = foo\ntwo = bar\n"
        )

    def test_junk(self):
        with self.assertRaises(Exception) as ec:
            fluent_parse("msg = value\n# Comment\n\nLine of junk")
        assert ec.exception.args == ('Expected token: "=" after message msg at line 3',)

    def test_file(self):
        bytes = get_test_resource("demo.ftl")
        res = fluent_parse(bytes, with_linepos=False)
        copyright = "Any copyright is dedicated to the Public Domain.\nhttp://creativecommons.org/publicdomain/zero/1.0/"
        entries = [
            Entry(
                id=("title",),
                value=PatternMessage(["About Localization"]),
                comment="Simple string",
            ),
            Entry(
                id=("feedbackUninstallCopy",),
                value=PatternMessage(
                    [
                        "Your participation in Firefox Test Pilot means\na lot! Please check out our other experiments,\nand stay tuned for more to come."
                    ]
                ),
                comment="Multiline string: press Shift + Enter to insert new line",
            ),
            Entry(
                id=("emailOptInInput",),
                value=PatternMessage([]),
                properties={"placeholder": PatternMessage(["email goes here :)"])},
                comment="Attributes: in original string",
            ),
            Entry(
                id=("file-menu",),
                value=PatternMessage([]),
                properties={
                    "label": PatternMessage(["File"]),
                    "accesskey": PatternMessage(["F"]),
                },
                comment="Attributes: access keys",
            ),
            Entry(
                id=("other-file-menu",),
                value=PatternMessage([]),
                properties={
                    "aria-label": PatternMessage(
                        [Expression("file-menu.label", "message")]
                    ),
                    "accesskey": PatternMessage(
                        [Expression("file-menu.accesskey", "message")]
                    ),
                },
            ),
            Entry(
                id=("shotIndexNoExpirationSymbol",),
                value=PatternMessage(["∞"]),
                properties={"title": PatternMessage(["This shot does not expire"])},
                comment="Value and an attribute",
            ),
            Entry(
                id=("delete-all-message",),
                value=SelectMessage(
                    declarations={"num_1": Expression(VariableRef("num"), "number")},
                    selectors=(VariableRef("num_1"),),
                    variants={
                        ("one",): ["Delete this download?"],
                        (CatchallKey("other"),): [
                            "Delete ",
                            Expression(VariableRef("num")),
                            " downloads?",
                        ],
                    },
                ),
                comment="Plurals",
            ),
            Entry(
                id=("delete-all-message-special-cases",),
                value=SelectMessage(
                    declarations={"num_1": Expression(VariableRef("num"), "number")},
                    selectors=(VariableRef("num_1"),),
                    variants={
                        ("12",): ["Delete this dozen of downloads?"],
                        ("2",): ["Delete this pair of downloads?"],
                        ("1",): ["Delete this download?"],
                        (CatchallKey("other"),): [
                            "Delete ",
                            Expression(VariableRef("num")),
                            " downloads?",
                        ],
                    },
                ),
                comment="Plurals with custom values",
            ),
            Entry(
                id=("today-is",),
                value=PatternMessage(
                    [
                        "Today is ",
                        Expression(
                            VariableRef("date"),
                            "datetime",
                            {"month": "long", "year": "numeric", "day": "numeric"},
                        ),
                    ],
                ),
                comment="DATETIME Built-in function",
            ),
            Entry(
                id=("default-content-process-count",),
                value=PatternMessage([]),
                properties={
                    "label": PatternMessage(
                        [Expression(VariableRef("num")), " (default)"]
                    )
                },
                comment="Soft Launch",
            ),
            Entry(
                id=("platform",),
                value=SelectMessage(
                    declarations={"_1": Expression(None, "platform")},
                    selectors=(VariableRef("_1"),),
                    variants={
                        ("win",): ["Options"],
                        (CatchallKey("other"),): ["Preferences"],
                    },
                ),
                comment="PLATFORM() selector",
            ),
            Entry(
                id=("number",),
                value=SelectMessage(
                    declarations={
                        "var_1": Expression(
                            VariableRef("var"), "number", {"type": "ordinal"}
                        )
                    },
                    selectors=(VariableRef("var_1"),),
                    variants={
                        ("1",): ["first"],
                        ("one",): [Expression(VariableRef("var")), "st"],
                        (CatchallKey("other"),): [Expression(VariableRef("var")), "nd"],
                    },
                ),
                comment="NUMBER() selector",
            ),
            Entry(
                id=("platform-attribute",),
                value=PatternMessage([]),
                properties={
                    "title": SelectMessage(
                        declarations={"_1": Expression(None, "platform")},
                        selectors=(VariableRef("_1"),),
                        variants={
                            ("win",): ["Options"],
                            (CatchallKey("other"),): ["Preferences"],
                        },
                    )
                },
                comment="PLATFORM() selector in attribute",
            ),
            Entry(
                id=("download-choose-folder",),
                value=PatternMessage([]),
                properties={
                    "label": SelectMessage(
                        declarations={"_1": Expression(None, "platform")},
                        selectors=(VariableRef("_1"),),
                        variants={
                            ("macos",): ["Choose…"],
                            (CatchallKey("other"),): ["Browse…"],
                        },
                    ),
                    "accesskey": SelectMessage(
                        declarations={"_1": Expression(None, "platform")},
                        selectors=(VariableRef("_1"),),
                        variants={("macos",): ["e"], (CatchallKey("other"),): ["o"]},
                    ),
                },
                comment="Double selector in attributes",
            ),
            Entry(
                id=("selector-multi",),
                value=SelectMessage(
                    declarations={
                        "num": Expression(VariableRef("num"), "number"),
                        "gender": Expression(VariableRef("gender"), "string"),
                    },
                    selectors=(VariableRef("num"), VariableRef("gender")),
                    variants={
                        ("one", "feminine"): ["There is one email for her"],
                        ("one", CatchallKey("masculine")): [
                            "There is one email for him"
                        ],
                        (CatchallKey("other"), "feminine"): [
                            "There are many emails for her"
                        ],
                        (CatchallKey("other"), CatchallKey("masculine")): [
                            "There are many emails for him"
                        ],
                    },
                ),
                comment="Multiple selectors",
            ),
            Entry(
                id=("-term",),
                value=PatternMessage(["Term"]),
                comment="Term",
            ),
            Entry(
                id=("term-reference",),
                value=PatternMessage(
                    ["Term ", Expression("-term", "message"), " Reference"],
                ),
                comment="TermReference",
            ),
            Entry(
                id=("string-expression",),
                value=PatternMessage([Expression("")]),
                comment="StringExpression",
            ),
            Entry(
                id=("number-expression",),
                value=PatternMessage([Expression("5", "number")]),
                comment="NumberExpression",
            ),
            Entry(
                id=("attribute-expression",),
                value=PatternMessage([Expression("my_id.title", "message")]),
                comment="MessageReference with attribute (was: AttributeExpression)",
            ),
            Entry(
                id=("selector-nested",),
                value=SelectMessage(
                    declarations={
                        "gender": Expression(VariableRef("gender"), "string"),
                        "num": Expression(VariableRef("num"), "number"),
                    },
                    selectors=(VariableRef("gender"), VariableRef("num")),
                    variants={
                        ("masculine", "one"): ["There is one email for him"],
                        ("masculine", CatchallKey("other")): [
                            "There are many emails for him"
                        ],
                        (CatchallKey("feminine"), "one"): [
                            "There is one email for her"
                        ],
                        (
                            CatchallKey("feminine"),
                            CatchallKey("other"),
                        ): ["There are many emails for her"],
                    },
                ),
                comment="Nested selectors",
            ),
        ]
        assert res == Resource(
            Format.fluent,
            meta=[Metadata("info", copyright)],
            comment="Resource Comment",
            sections=[Section(id=(), entries=entries)],
        )
        assert "".join(fluent_serialize(res)) == dedent(
            """\
            # Any copyright is dedicated to the Public Domain.
            # http://creativecommons.org/publicdomain/zero/1.0/


            ### Resource Comment

            # Simple string
            title = About Localization
            # Multiline string: press Shift + Enter to insert new line
            feedbackUninstallCopy =
                Your participation in Firefox Test Pilot means
                a lot! Please check out our other experiments,
                and stay tuned for more to come.
            # Attributes: in original string
            emailOptInInput =
                .placeholder = email goes here :)
            # Attributes: access keys
            file-menu =
                .label = File
                .accesskey = F
            other-file-menu =
                .aria-label = { file-menu.label }
                .accesskey = { file-menu.accesskey }
            # Value and an attribute
            shotIndexNoExpirationSymbol = ∞
                .title = This shot does not expire
            # Plurals
            delete-all-message =
                { $num ->
                    [one] Delete this download?
                   *[other] Delete { $num } downloads?
                }
            # Plurals with custom values
            delete-all-message-special-cases =
                { $num ->
                    [1] Delete this download?
                    [2] Delete this pair of downloads?
                    [12] Delete this dozen of downloads?
                   *[other] Delete { $num } downloads?
                }
            # DATETIME Built-in function
            today-is = Today is { DATETIME($date, month: "long", year: "numeric", day: "numeric") }
            # Soft Launch
            default-content-process-count =
                .label = { $num } (default)
            # PLATFORM() selector
            platform =
                { PLATFORM() ->
                    [win] Options
                   *[other] Preferences
                }
            # NUMBER() selector
            number =
                { NUMBER($var, type: "ordinal") ->
                    [1] first
                    [one] { $var }st
                   *[other] { $var }nd
                }
            # PLATFORM() selector in attribute
            platform-attribute =
                .title =
                    { PLATFORM() ->
                        [win] Options
                       *[other] Preferences
                    }
            # Double selector in attributes
            download-choose-folder =
                .label =
                    { PLATFORM() ->
                        [macos] Choose…
                       *[other] Browse…
                    }
                .accesskey =
                    { PLATFORM() ->
                        [macos] e
                       *[other] o
                    }
            # Multiple selectors
            selector-multi =
                { $num ->
                    [one]
                        { $gender ->
                            [feminine] There is one email for her
                           *[masculine] There is one email for him
                        }
                   *[other]
                        { $gender ->
                            [feminine] There are many emails for her
                           *[masculine] There are many emails for him
                        }
                }
            # Term
            -term = Term
            # TermReference
            term-reference = Term { -term } Reference
            # StringExpression
            string-expression = { "" }
            # NumberExpression
            number-expression = { 5 }
            # MessageReference with attribute (was: AttributeExpression)
            attribute-expression = { my_id.title }
            # Nested selectors
            selector-nested =
                { $gender ->
                    [masculine]
                        { $num ->
                            [one] There is one email for him
                           *[other] There are many emails for him
                        }
                   *[feminine]
                        { $num ->
                            [one] There is one email for her
                           *[other] There are many emails for her
                        }
                }
            """
        )
