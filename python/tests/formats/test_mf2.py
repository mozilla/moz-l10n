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

from json import load
from os.path import dirname
from pathlib import Path
from typing import Any

import pytest
from jsonschema import validate
from moz.l10n.formats.mf2 import (
    MF2ParseError,
    mf2_parse_message,
    mf2_serialize_message,
    mf2_to_json,
)
from moz.l10n.formats.mf2.from_json import mf2_from_json
from moz.l10n.message import message_from_json, message_to_json
from moz.l10n.model import (
    CatchallKey,
    Expression,
    Markup,
    Message,
    PatternMessage,
    SelectMessage,
    VariableRef,
)

schemas = Path(dirname(__file__)) / "../../../schemas"
mf2_schema: dict[str, dict[str, Any]] = load((schemas / "mf2-message.json").open())
moz_schema: dict[str, dict[str, Any]] = load((schemas / "message.json").open())


def ok(src: str, exp_msg: Message, exp_str: str | None = None):
    msg = mf2_parse_message(src)
    assert msg == exp_msg
    assert mf2_serialize_message(msg) == exp_str or src

    mf2_json = mf2_to_json(msg)
    validate(mf2_json, mf2_schema)
    msg2 = mf2_from_json(mf2_json)
    assert msg2 == msg

    # These tests are for the moz.l10n.message converters rather than any MF2 code,
    # included here to avoid duplicating this test suite.
    moz_json = message_to_json(msg)
    validate(moz_json, moz_schema)
    msg3 = message_from_json(moz_json)
    assert msg3 == msg


def fail(src: str) -> str:
    with pytest.raises(MF2ParseError) as err_info:
        mf2_parse_message(src)
    return err_info.value.args[0]


def test_pattern():
    ok("pattern", PatternMessage(["pattern"]))
    ok(" pattern ", PatternMessage([" pattern "]))
    ok(
        "text1 {$var} text2 {#m:open}text3{/m:close}{#m:standalone/}",
        PatternMessage(
            [
                "text1 ",
                Expression(VariableRef("var")),
                " text2 ",
                Markup("open", "m:open"),
                "text3",
                Markup("close", "m:close"),
                Markup("standalone", "m:standalone"),
            ]
        ),
    )
    fail("pattern}")
    fail("pattern{{quoted}}")
    fail("pattern}}")


def test_quoted_pattern():
    ok("{{quoted}}", PatternMessage(["quoted"]), "quoted")
    ok(" {{quoted}} ", PatternMessage(["quoted"]), "quoted")
    fail("{{quoted}} x")
    fail("{{quoted}} {{more}}")
    fail("{{quoted}")
    fail("{{quoted")


def test_placeholder():
    fail("{")
    fail("{}")
    fail("{ }")

    ok("{name}", PatternMessage([Expression("name")]))
    ok("{ name }", PatternMessage([Expression("name")]), "{name}")
    ok("{42}", PatternMessage([Expression("42")]))
    ok("{42.99}", PatternMessage([Expression("42.99")]))
    ok("{-13e-09}", PatternMessage([Expression("-13e-09")]))
    fail("{42.99.13}")
    fail("{-name}")

    ok("{|quoted|}", PatternMessage([Expression("quoted")]), "{quoted}")
    ok("{|quoted}|}", PatternMessage([Expression("quoted}")]))
    ok(r"{|quoted\\\|escapes|}", PatternMessage([Expression("quoted\\|escapes")]))
    fail("{|quoted}")

    ok("{$var}", PatternMessage([Expression(VariableRef("var"))]))
    ok("{ $var }", PatternMessage([Expression(VariableRef("var"))]), "{$var}")
    ok("{$foo.bar}", PatternMessage([Expression(VariableRef("foo.bar"))]))


def test_placeholder_attributes():
    fail("{@foo}")
    ok("{42 @foo}", PatternMessage([Expression("42", attributes={"foo": True})]))
    ok(
        "{42 @foo = 13 }",
        PatternMessage([Expression("42", attributes={"foo": "13"})]),
        "{42 @foo=13}",
    )
    ok(
        "{42 @foo=| 13 |}",
        PatternMessage([Expression("42", attributes={"foo": " 13 "})]),
    )
    fail("{42 @foo=$var}")
    ok(
        "{$var @foo @bar=baz}",
        PatternMessage(
            [Expression(VariableRef("var"), attributes={"foo": True, "bar": "baz"})]
        ),
    )
    fail("{$var@foo}")
    fail("{42 @foo @foo}")
    fail("{$var :string@foo}")
    fail("{$var :string @foo opt=42}")


def test_placeholder_with_function():
    ok("{:string}", PatternMessage([Expression(None, "string")]))
    ok("{$var :string}", PatternMessage([Expression(VariableRef("var"), "string")]))
    ok(
        "{ $var :string }",
        PatternMessage([Expression(VariableRef("var"), "string")]),
        "{$var :string}",
    )
    fail("{$var:string}")

    ok(
        "{$var :string opt=42}",
        PatternMessage([Expression(VariableRef("var"), "string", {"opt": "42"})]),
    )
    ok(
        "{$var :string opt = 42}",
        PatternMessage([Expression(VariableRef("var"), "string", {"opt": "42"})]),
        "{$var :string opt=42}",
    )
    fail("{$var opt=42}")
    ok(
        "{$var :test:string opt-a=42 opt:b=$var}",
        PatternMessage(
            [
                Expression(
                    VariableRef("var"),
                    "test:string",
                    {"opt-a": "42", "opt:b": VariableRef("var")},
                )
            ]
        ),
    )
    fail("{$var :string opt=42 opt=13}")
    fail("{$var :string opt-a=|x|opt-b=42}")

    ok(
        "{$var :test:string opt-a=42 opt:b=$var @foo @bar=baz}",
        PatternMessage(
            [
                Expression(
                    VariableRef("var"),
                    "test:string",
                    {"opt-a": "42", "opt:b": VariableRef("var")},
                    attributes={"foo": True, "bar": "baz"},
                ),
            ]
        ),
    )


def test_markup():
    ok(
        "{#aa}{/bb}{#cc/}",
        PatternMessage(
            [Markup("open", "aa"), Markup("close", "bb"), Markup("standalone", "cc")]
        ),
    )
    ok(
        "{ #aa }{ /bb }{ #cc /}",
        PatternMessage(
            [Markup("open", "aa"), Markup("close", "bb"), Markup("standalone", "cc")]
        ),
        "{#aa}{/bb}{#cc/}",
    )
    ok(
        "{#aa:AA}{/bb:BB}{#cc:CC/}",
        PatternMessage(
            [
                Markup("open", "aa:AA"),
                Markup("close", "bb:BB"),
                Markup("standalone", "cc:CC"),
            ]
        ),
    )
    fail("{#aa")
    fail("{#cc/ }")
    fail("{/bb/}")
    fail("{#aa :string}")

    ok(
        "{#aa opt=42}{/bb opt=42}{#cc opt=42/}",
        PatternMessage(
            [
                Markup("open", "aa", {"opt": "42"}),
                Markup("close", "bb", {"opt": "42"}),
                Markup("standalone", "cc", {"opt": "42"}),
            ]
        ),
    )
    ok(
        "{#aa @attr}{/bb @attr=42}{#cc @ns:attr=|42|/}",
        PatternMessage(
            [
                Markup("open", "aa", attributes={"attr": True}),
                Markup("close", "bb", attributes={"attr": "42"}),
                Markup("standalone", "cc", attributes={"ns:attr": "42"}),
            ]
        ),
        "{#aa @attr}{/bb @attr=42}{#cc @ns:attr=42/}",
    )
    ok(
        "{#aa opt=42 @attr=x}",
        PatternMessage([Markup("open", "aa", {"opt": "42"}, {"attr": "x"})]),
    )
    fail("{#aa @attr=x opt=42}")
    fail("{#aa@attr}")
    fail("{#aa opt=x@attr}")
    fail("{#aa opt=|x|@attr}")


def test_declarations():
    ok(
        ".input {$var}\n{{quoted}}",
        PatternMessage(
            declarations={"var": Expression(VariableRef("var"))},
            pattern=["quoted"],
        ),
    )
    ok(
        ".input{$var}{{quoted}}",
        PatternMessage(
            declarations={"var": Expression(VariableRef("var"))},
            pattern=["quoted"],
        ),
        ".input {$var}\n{{quoted}}",
    )
    fail(".input {42} {{quoted}}")

    ok(
        ".local $var = {42}\n{{quoted}}",
        PatternMessage(
            declarations={"var": Expression("42")},
            pattern=["quoted"],
        ),
    )
    ok(
        ".local $var2 = {$var1}\n{{quoted}}",
        PatternMessage(
            declarations={"var2": Expression(VariableRef("var1"))},
            pattern=["quoted"],
        ),
    )

    ok(
        ".input {$var1} .local $var2 = {$var1} {{quoted}}",
        PatternMessage(
            declarations={
                "var1": Expression(VariableRef("var1")),
                "var2": Expression(VariableRef("var1")),
            },
            pattern=["quoted"],
        ),
        ".input {$var1}\n.local $var2 = {$var1}\n{{quoted}}",
    )
    ok(
        ".input {$var1} .local $var2 = {42 :number opt=$var1} {{quoted}}",
        PatternMessage(
            declarations={
                "var1": Expression(VariableRef("var1")),
                "var2": Expression("42", "number", {"opt": VariableRef("var1")}),
            },
            pattern=["quoted"],
        ),
        ".input {$var1}\n.local $var2 = {42 :number opt=$var1}\n{{quoted}}",
    )

    fail(".local $var = {$var} {{quoted}}")
    fail(".input {$var} .input {$var} {{quoted}}")
    fail(".input {$var} .local $var = {42} {{quoted}}")
    fail(".local $var = {42} .input {$var} {{quoted}}")
    fail(".local $var1 = {$var2} .local $var2 = {42} {{quoted}}")

    ok(
        ".input {$foo :string} .local $bar = {42 :number} {{Hello {$foo}{$bar}}}",
        PatternMessage(
            declarations={
                "foo": Expression(VariableRef("foo"), "string"),
                "bar": Expression("42", "number"),
            },
            pattern=[
                "Hello ",
                Expression(VariableRef("foo")),
                Expression(VariableRef("bar")),
            ],
        ),
        ".input {$foo :string}\n.local $bar = {42 :number}\n"
        + "{{Hello {$foo}{$bar}}}",
    )


def test_select_message():
    ok(
        ".input{$foo :string}.match $foo *{{variant}}",
        SelectMessage(
            declarations={"foo": Expression(VariableRef("foo"), "string")},
            selectors=(VariableRef("foo"),),
            variants={(CatchallKey(),): ["variant"]},
        ),
        ".input {$foo :string}\n.match $foo\n* {{variant}}",
    )

    ok(
        """
        .input {$var :string}
        .match $var
        key {{one}}
        * {{two}}
        """,
        SelectMessage(
            declarations={"var": Expression(VariableRef("var"), "string")},
            selectors=(VariableRef("var"),),
            variants={("key",): ["one"], (CatchallKey(),): ["two"]},
        ),
        ".input {$var :string}\n.match $var\nkey {{one}}\n* {{two}}",
    )

    fail(".match $var * {{quoted}}")
    fail(
        """
            .input {$var :string}
            .match $var
            key {{one}}
            key {{repeat}}
            * {{other}}
            """
    )

    ok(
        """
        .input {$foo :string}
        .local $bar = {$foo}
        .match $foo $bar
        key |quoted key| {{one}}
        key |*| {{two}}
        * key {{three}}
        * * {{four}}
        """,
        SelectMessage(
            declarations={
                "foo": Expression(VariableRef("foo"), "string"),
                "bar": Expression(VariableRef("foo")),
            },
            selectors=(VariableRef("foo"), VariableRef("bar")),
            variants={
                ("key", "quoted key"): ["one"],
                ("key", "*"): ["two"],
                (CatchallKey(), "key"): ["three"],
                (CatchallKey(), CatchallKey()): ["four"],
            },
        ),
        ".input {$foo :string}\n.local $bar = {$foo}\n.match $foo $bar\n"
        + "key |quoted key| {{one}}\n"
        + "key |*| {{two}}\n"
        + "* key {{three}}\n"
        + "* * {{four}}",
    )

    fail(".input {$foo} .match $foo key {{one}}").startswith("Missing fallback variant")
    fail(".input {$foo} .match $foo * {{one}}").startswith(
        "Missing selector annotation"
    )
