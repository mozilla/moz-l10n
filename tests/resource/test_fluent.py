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

from fluent.syntax import ast as ftl

from moz.l10n.message import (
    CatchallKey,
    Expression,
    FunctionAnnotation,
    PatternMessage,
    SelectMessage,
    VariableRef,
)
from moz.l10n.resource.data import Comment, Entry, Metadata, Resource, Section
from moz.l10n.resource.fluent import fluent_parse, fluent_serialize
from moz.l10n.resource.format import Format

# Show full diff in self.assertEqual. https://stackoverflow.com/a/61345284
# __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999


class TestFluent(TestCase):
    def test_fluent_value(self):
        source = dedent(
            """\
            key =
                pre { $a ->
                    [1] One
                   *[2] Two
                } mid { $b ->
                   *[bb] BB
                    [cc] CC
                } post
                .attr = foo
            """
        )
        res = fluent_parse(source, as_ftl_patterns=True)
        self.assertEqual(len(res.sections), 1)
        self.assertEqual(len(res.sections[0].entries), 2)
        self.assertEqual(res.sections[0].entries[0].id, ("key",))
        self.assertIsInstance(res.sections[0].entries[0].value, ftl.Pattern)
        self.assertEqual(res.sections[0].entries[1].id, ("key", "attr"))
        self.assertIsInstance(res.sections[0].entries[1].value, ftl.Pattern)
        self.assertEqual("".join(fluent_serialize(res)), source)

    def test_equality_same(self):
        source = 'progress = Progress: { NUMBER($num, style: "percent") }.'
        res1 = fluent_parse(source)
        res2 = fluent_parse(source)
        self.assertEqual(res1, res2)

    def test_equality_different_whitespace(self):
        source1 = b"foo = { $arg }"
        source2 = b"foo = {    $arg    }"
        res1 = fluent_parse(source1)
        res2 = fluent_parse(source2)
        self.assertEqual(res1, res2)

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
                        Expression("msg.foo", FunctionAnnotation("message")),
                        " C ",
                        Expression("-term", FunctionAnnotation("message", {"x": "42"})),
                    ]
                ),
                comment="Message Comment\non two lines.",
            ),
            Entry(
                ("functions",),
                PatternMessage(
                    [
                        Expression(VariableRef("arg"), FunctionAnnotation("number")),
                        Expression("bar", FunctionAnnotation("foo", {"opt": "val"})),
                    ]
                ),
            ),
            Entry(("has-attr",), PatternMessage(["ABC"])),
            Entry(("has-attr", "attr"), PatternMessage(["Attr"])),
            Entry(
                ("has-only-attr", "attr"),
                PatternMessage(["Attr"]),
                comment="Attr Comment",
            ),
            Entry(
                ("single-sel",),
                SelectMessage(
                    [Expression(VariableRef("num"), FunctionAnnotation("number"))],
                    {
                        ("one",): ["One"],
                        (other,): ["Other"],
                    },
                ),
            ),
            Entry(
                ("two-sels",),
                SelectMessage(
                    [
                        Expression(VariableRef("a"), FunctionAnnotation("number")),
                        Expression(VariableRef("b"), FunctionAnnotation("string")),
                    ],
                    {
                        ("1", "cc"): ["pre One mid CC post"],
                        ("1", CatchallKey("bb")): ["pre One mid BB post"],
                        (CatchallKey("2"), "cc"): ["pre Two mid CC post"],
                        (CatchallKey("2"), CatchallKey("bb")): ["pre Two mid BB post"],
                    },
                ),
            ),
            Entry(
                ("deep-sels",),
                SelectMessage(
                    [
                        Expression(VariableRef("a"), FunctionAnnotation("number")),
                        Expression(VariableRef("b"), FunctionAnnotation("number")),
                    ],
                    {
                        ("0", "one"): [Expression("")],
                        ("0", other): ["0,x"],
                        ("one", "one"): [Expression("1,1")],
                        ("one", other): ["1,x"],
                        (other, "0"): ["x,0"],
                        (other, "one"): ["x,1"],
                        (other, other): ["x,x"],
                    },
                ),
            ),
        ]
        self.assertEqual(
            res,
            Resource(
                Format.fluent,
                [
                    Section(
                        id=(),
                        entries=[
                            Entry(("simple",), PatternMessage(["A"])),
                            Comment("Standalone Comment"),
                        ],
                        comment="Group Comment",
                    ),
                    Section((), entries),
                ],
                comment="Resource Comment",
            ),
        )
        self.assertEqual(
            "".join(fluent_serialize(res)),
            dedent(
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
                    { NUMBER($num) ->
                        [one] One
                       *[other] Other
                    }
                two-sels =
                    { NUMBER($a) ->
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
                    { NUMBER($a) ->
                        [0]
                            { NUMBER($b) ->
                                [one] { "" }
                               *[other] 0,x
                            }
                        [one]
                            { NUMBER($b) ->
                                [one] { "1,1" }
                               *[other] 1,x
                            }
                       *[other]
                            { NUMBER($b) ->
                                [0] x,0
                                [one] x,1
                               *[other] x,x
                            }
                    }
                """
            ),
        )
        self.assertEqual(
            "".join(fluent_serialize(res, trim_comments=True)),
            dedent(
                """\
                simple = A
                expressions = A { $arg } B { msg.foo } C { -term(x: 42) }
                functions = { NUMBER($arg) }{ FOO("bar", opt: "val") }
                has-attr = ABC
                    .attr = Attr
                has-only-attr =
                    .attr = Attr
                single-sel =
                    { NUMBER($num) ->
                        [one] One
                       *[other] Other
                    }
                two-sels =
                    { NUMBER($a) ->
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
                    { NUMBER($a) ->
                        [0]
                            { NUMBER($b) ->
                                [one] { "" }
                               *[other] 0,x
                            }
                        [one]
                            { NUMBER($b) ->
                                [one] { "1,1" }
                               *[other] 1,x
                            }
                       *[other]
                            { NUMBER($b) ->
                                [0] x,0
                                [one] x,1
                               *[other] x,x
                            }
                    }
                """
            ),
        )

    def test_attr_comment(self):
        res = fluent_parse("msg = body\n  .attr = value")

        res.sections[0].entries[1].comment = "comment1"
        self.assertEqual(
            "".join(fluent_serialize(res)),
            dedent(
                """\
                # attr:
                # comment1
                msg = body
                    .attr = value
                """
            ),
        )
        self.assertEqual(
            "".join(fluent_serialize(res, trim_comments=True)),
            "msg = body\n    .attr = value\n",
        )

        res.sections[0].entries[0].comment = "comment0"
        self.assertEqual(
            "".join(fluent_serialize(res)),
            dedent(
                """\
                # comment0
                #
                # attr:
                # comment1
                msg = body
                    .attr = value
                """
            ),
        )
        self.assertEqual(
            "".join(fluent_serialize(res, trim_comments=True)),
            "msg = body\n    .attr = value\n",
        )

    def test_meta(self):
        res = fluent_parse("one = foo\ntwo = bar")
        res.sections[0].entries[1].meta = [Metadata("a", 42), Metadata("b", False)]
        try:
            "".join(fluent_serialize(res))
            raise Exception("Expected an error")
        except Exception as e:
            self.assertEqual(
                e.args, ("Metadata requires serialize_metadata parameter",)
            )
        self.assertEqual(
            "".join(fluent_serialize(res, lambda _: None)), "one = foo\ntwo = bar\n"
        )
        self.assertEqual(
            "".join(fluent_serialize(res, lambda m: f"@{m.key}: {m.value}")),
            dedent(
                """\
                one = foo
                # @a: 42
                # @b: False
                two = bar
                """
            ),
        )
        self.assertEqual(
            "".join(fluent_serialize(res, trim_comments=True)), "one = foo\ntwo = bar\n"
        )

    def test_junk(self):
        with self.assertRaisesRegex(Exception, 'Expected token: "="'):
            fluent_parse("msg = value\n# Comment\nLine of junk", as_ftl_patterns=True)

    def test_file(self):
        bytes = files("tests.resource.data").joinpath("demo.ftl").read_bytes()
        res = fluent_parse(bytes)
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
                id=("emailOptInInput", "placeholder"),
                value=PatternMessage(["email goes here :)"]),
                comment="Attributes: in original string",
            ),
            Entry(
                id=("file-menu", "label"),
                value=PatternMessage(["File"]),
                comment="Attributes: access keys",
            ),
            Entry(
                id=("file-menu", "accesskey"),
                value=PatternMessage(["F"]),
            ),
            Entry(
                id=("other-file-menu", "aria-label"),
                value=PatternMessage(
                    [Expression("file-menu.label", FunctionAnnotation("message"))],
                ),
            ),
            Entry(
                id=("other-file-menu", "accesskey"),
                value=PatternMessage(
                    [Expression("file-menu.accesskey", FunctionAnnotation("message"))],
                ),
            ),
            Entry(
                id=("shotIndexNoExpirationSymbol",),
                value=PatternMessage(["∞"]),
                comment="Value and an attribute",
            ),
            Entry(
                id=("shotIndexNoExpirationSymbol", "title"),
                value=PatternMessage(["This shot does not expire"]),
            ),
            Entry(
                id=("delete-all-message",),
                value=SelectMessage(
                    selectors=[
                        Expression(VariableRef("num"), FunctionAnnotation("number"))
                    ],
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
                    selectors=[
                        Expression(VariableRef("num"), FunctionAnnotation("number"))
                    ],
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
                            FunctionAnnotation(
                                "datetime",
                                {"month": "long", "year": "numeric", "day": "numeric"},
                            ),
                        ),
                    ],
                ),
                comment="DATETIME Built-in function",
            ),
            Entry(
                id=("default-content-process-count", "label"),
                value=PatternMessage([Expression(VariableRef("num")), " (default)"]),
                comment="Soft Launch",
            ),
            Entry(
                id=("platform",),
                value=SelectMessage(
                    selectors=[Expression(None, FunctionAnnotation("platform"))],
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
                    selectors=[
                        Expression(
                            VariableRef("var"),
                            FunctionAnnotation("number", {"type": "ordinal"}),
                        )
                    ],
                    variants={
                        ("1",): ["first"],
                        ("one",): [Expression(VariableRef("var")), "st"],
                        (CatchallKey("other"),): [Expression(VariableRef("var")), "nd"],
                    },
                ),
                comment="NUMBER() selector",
            ),
            Entry(
                id=("platform-attribute", "title"),
                value=SelectMessage(
                    selectors=[Expression(None, FunctionAnnotation("platform"))],
                    variants={
                        ("win",): ["Options"],
                        (CatchallKey("other"),): ["Preferences"],
                    },
                ),
                comment="PLATFORM() selector in attribute",
            ),
            Entry(
                id=("download-choose-folder", "label"),
                value=SelectMessage(
                    selectors=[Expression(None, FunctionAnnotation("platform"))],
                    variants={
                        ("macos",): ["Choose…"],
                        (CatchallKey("other"),): ["Browse…"],
                    },
                ),
                comment="Double selector in attributes",
            ),
            Entry(
                id=("download-choose-folder", "accesskey"),
                value=SelectMessage(
                    selectors=[Expression(None, FunctionAnnotation("platform"))],
                    variants={("macos",): ["e"], (CatchallKey("other"),): ["o"]},
                ),
            ),
            Entry(
                id=("selector-multi",),
                value=SelectMessage(
                    selectors=[
                        Expression(VariableRef("num"), FunctionAnnotation("number")),
                        Expression(VariableRef("gender"), FunctionAnnotation("string")),
                    ],
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
                    [
                        "Term ",
                        Expression("-term", FunctionAnnotation("message")),
                        " Reference",
                    ],
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
                value=PatternMessage(
                    [Expression("5", FunctionAnnotation("number"))],
                ),
                comment="NumberExpression",
            ),
            Entry(
                id=("attribute-expression",),
                value=PatternMessage(
                    [Expression("my_id.title", FunctionAnnotation("message"))],
                ),
                comment="MessageReference with attribute (was: AttributeExpression)",
            ),
            Entry(
                id=("selector-nested",),
                value=SelectMessage(
                    selectors=[
                        Expression(VariableRef("gender"), FunctionAnnotation("string")),
                        Expression(VariableRef("num"), FunctionAnnotation("number")),
                    ],
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
        self.assertEqual(
            res, Resource(Format.fluent, sections=[Section(id=(), entries=entries)])
        )
        self.assertEqual(
            "".join(fluent_serialize(res)),
            dedent(
                """\
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
                    { NUMBER($num) ->
                        [one] Delete this download?
                       *[other] Delete { $num } downloads?
                    }
                # Plurals with custom values
                delete-all-message-special-cases =
                    { NUMBER($num) ->
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
                    { NUMBER($num) ->
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
                            { NUMBER($num) ->
                                [one] There is one email for him
                               *[other] There are many emails for him
                            }
                       *[feminine]
                            { NUMBER($num) ->
                                [one] There is one email for her
                               *[other] There are many emails for her
                            }
                    }
                """
            ),
        )
