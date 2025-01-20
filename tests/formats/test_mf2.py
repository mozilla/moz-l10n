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

import pytest

from moz.l10n.formats.mf2 import MF2ParseError, mf2_parse_message, mf2_serialize_message
from moz.l10n.message.data import (
    CatchallKey,
    Expression,
    Markup,
    Message,
    PatternMessage,
    SelectMessage,
    VariableRef,
)


def fail(src: str) -> str:
    with pytest.raises(MF2ParseError) as err_info:
        mf2_parse_message(src)
    return err_info.value.args[0]


def msg_str(msg: Message):
    return "".join(mf2_serialize_message(msg))


def test_pattern():
    msg = mf2_parse_message("pattern")
    assert msg == PatternMessage(["pattern"])
    assert msg_str(msg) == "pattern"

    msg = mf2_parse_message(" pattern ")
    assert msg == PatternMessage([" pattern "])
    assert msg_str(msg) == " pattern "

    src = "text1 {$var} text2 {#m:open}text3{/m:close}{#m:standalone/}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage(
        [
            "text1 ",
            Expression(VariableRef("var")),
            " text2 ",
            Markup("open", "m:open"),
            "text3",
            Markup("close", "m:close"),
            Markup("standalone", "m:standalone"),
        ]
    )
    assert msg_str(msg) == src

    fail("pattern}")

    fail("pattern{{quoted}}")

    fail("pattern}}")


def test_quoted_pattern():
    msg = mf2_parse_message("{{quoted}}")
    assert msg == PatternMessage(["quoted"])
    assert msg_str(msg) == "quoted"

    msg = mf2_parse_message(" {{quoted}} ")
    assert msg == PatternMessage(["quoted"])
    assert msg_str(msg) == "quoted"

    fail("{{quoted}} x")
    fail("{{quoted}} {{more}}")
    fail("{{quoted}")
    fail("{{quoted")


def test_placeholder():
    fail("{")
    fail("{}")
    fail("{ }")

    msg = mf2_parse_message("{name}")
    assert msg == PatternMessage([Expression("name")])
    assert msg_str(msg) == "{name}"

    msg = mf2_parse_message("{ name }")
    assert msg == PatternMessage([Expression("name")])
    assert msg_str(msg) == "{name}"

    msg = mf2_parse_message("{42}")
    assert msg == PatternMessage([Expression("42")])
    assert msg_str(msg) == "{42}"

    msg = mf2_parse_message("{42.99}")
    assert msg == PatternMessage([Expression("42.99")])
    assert msg_str(msg) == "{42.99}"

    msg = mf2_parse_message("{-13e-09}")
    assert msg == PatternMessage([Expression("-13e-09")])
    assert msg_str(msg) == "{-13e-09}"

    fail("{42.99.13}")
    fail("{-name}")

    msg = mf2_parse_message("{|quoted|}")
    assert msg == PatternMessage([Expression("quoted")])
    assert msg_str(msg) == "{quoted}"

    msg = mf2_parse_message("{|quoted}|}")
    assert msg == PatternMessage([Expression("quoted}")])
    assert msg_str(msg) == "{|quoted}|}"

    src = r"{|quoted\\\|escapes|}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage([Expression("quoted\\|escapes")])
    assert msg_str(msg) == src

    fail("{|quoted}")

    msg = mf2_parse_message("{$var}")
    assert msg == PatternMessage([Expression(VariableRef("var"))])
    assert msg_str(msg) == "{$var}"

    msg = mf2_parse_message("{ $var }")
    assert msg == PatternMessage([Expression(VariableRef("var"))])
    assert msg_str(msg) == "{$var}"

    msg = mf2_parse_message("{$foo.bar}")
    assert msg == PatternMessage([Expression(VariableRef("foo.bar"))])
    assert msg_str(msg) == "{$foo.bar}"


def test_placeholder_attributes():
    fail("{@foo}")

    src = "{42 @foo}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage([Expression("42", attributes={"foo": None})])
    assert msg_str(msg) == src

    msg = mf2_parse_message("{42 @foo = 13 }")
    assert msg == PatternMessage([Expression("42", attributes={"foo": "13"})])
    assert msg_str(msg) == "{42 @foo=13}"

    src = "{42 @foo=| 13 |}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage([Expression("42", attributes={"foo": " 13 "})])
    assert msg_str(msg) == src

    fail("{42 @foo=$var}")

    src = "{$var @foo @bar=baz}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage(
        [Expression(VariableRef("var"), attributes={"foo": None, "bar": "baz"})]
    )
    assert msg_str(msg) == src

    fail("{$var@foo}")
    fail("{42 @foo @foo}")
    fail("{$var :string@foo}")
    fail("{$var :string @foo opt=42}")


def test_placeholder_with_function():
    msg = mf2_parse_message("{$var :string}")
    assert msg == PatternMessage([Expression(VariableRef("var"), "string")])
    assert msg_str(msg) == "{$var :string}"

    msg = mf2_parse_message("{ $var :string }")
    assert msg == PatternMessage([Expression(VariableRef("var"), "string")])
    assert msg_str(msg) == "{$var :string}"

    fail("{$var:string}")

    msg = mf2_parse_message("{$var :string opt=42}")
    assert msg == PatternMessage(
        [Expression(VariableRef("var"), "string", {"opt": "42"})]
    )
    assert msg_str(msg) == "{$var :string opt=42}"

    msg = mf2_parse_message("{$var :string opt = 42}")
    assert msg == PatternMessage(
        [Expression(VariableRef("var"), "string", {"opt": "42"})]
    )
    assert msg_str(msg) == "{$var :string opt=42}"

    fail("{$var opt=42}")

    src = "{$var :test:string opt-a=42 opt:b=$var}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage(
        [
            Expression(
                VariableRef("var"),
                "test:string",
                {"opt-a": "42", "opt:b": VariableRef("var")},
            )
        ]
    )
    assert msg_str(msg) == src

    fail("{$var :string opt=42 opt=13}")
    fail("{$var :string opt-a=|x|opt-b=42}")

    src = "{$var :test:string opt-a=42 opt:b=$var @foo @bar=baz}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage(
        [
            Expression(
                VariableRef("var"),
                "test:string",
                {"opt-a": "42", "opt:b": VariableRef("var")},
                attributes={"foo": None, "bar": "baz"},
            ),
        ]
    )
    assert msg_str(msg) == src


def test_markup():
    src = "{#aa}{/bb}{#cc/}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage(
        [Markup("open", "aa"), Markup("close", "bb"), Markup("standalone", "cc")]
    )
    assert msg_str(msg) == src

    msg = mf2_parse_message("{ #aa }{ /bb }{ #cc /}")
    assert msg == PatternMessage(
        [Markup("open", "aa"), Markup("close", "bb"), Markup("standalone", "cc")]
    )
    assert msg_str(msg) == "{#aa}{/bb}{#cc/}"

    src = "{#aa:AA}{/bb:BB}{#cc:CC/}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage(
        [
            Markup("open", "aa:AA"),
            Markup("close", "bb:BB"),
            Markup("standalone", "cc:CC"),
        ]
    )
    assert msg_str(msg) == src

    fail("{#aa")
    fail("{#cc/ }")
    fail("{/bb/}")
    fail("{#aa :string}")

    src = "{#aa opt=42}{/bb opt=42}{#cc opt=42/}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage(
        [
            Markup("open", "aa", {"opt": "42"}),
            Markup("close", "bb", {"opt": "42"}),
            Markup("standalone", "cc", {"opt": "42"}),
        ]
    )
    assert msg_str(msg) == src

    msg = mf2_parse_message("{#aa @attr}{/bb @attr=42}{#cc @ns:attr=|42|/}")
    assert msg == PatternMessage(
        [
            Markup("open", "aa", attributes={"attr": None}),
            Markup("close", "bb", attributes={"attr": "42"}),
            Markup("standalone", "cc", attributes={"ns:attr": "42"}),
        ]
    )
    assert msg_str(msg) == "{#aa @attr}{/bb @attr=42}{#cc @ns:attr=42/}"

    src = "{#aa opt=42 @attr=x}"
    msg = mf2_parse_message(src)
    assert msg == PatternMessage([Markup("open", "aa", {"opt": "42"}, {"attr": "x"})])
    assert msg_str(msg) == src

    fail("{#aa @attr=x opt=42}")
    fail("{#aa@attr}")
    fail("{#aa opt=x@attr}")
    fail("{#aa opt=|x|@attr}")


def test_declarations():
    msg = mf2_parse_message(".input {$var} {{quoted}}")
    assert msg == PatternMessage(
        declarations={"var": Expression(VariableRef("var"))},
        pattern=["quoted"],
    )
    assert msg_str(msg) == ".input {$var}\n{{quoted}}"

    msg = mf2_parse_message(".input{$var}{{quoted}}")
    assert msg == PatternMessage(
        declarations={"var": Expression(VariableRef("var"))},
        pattern=["quoted"],
    )
    assert msg_str(msg) == ".input {$var}\n{{quoted}}"

    fail(".input {42} {{quoted}}")

    msg = mf2_parse_message(".local $var = {42} {{quoted}}")
    assert msg == PatternMessage(
        declarations={"var": Expression("42")},
        pattern=["quoted"],
    )
    assert msg_str(msg) == ".local $var = {42}\n{{quoted}}"

    msg = mf2_parse_message(".local $var2 = {$var1} {{quoted}}")
    assert msg == PatternMessage(
        declarations={"var2": Expression(VariableRef("var1"))},
        pattern=["quoted"],
    )
    assert msg_str(msg) == ".local $var2 = {$var1}\n{{quoted}}"

    msg = mf2_parse_message(".input {$var1} .local $var2 = {$var1} {{quoted}}")
    assert msg == PatternMessage(
        declarations={
            "var1": Expression(VariableRef("var1")),
            "var2": Expression(VariableRef("var1")),
        },
        pattern=["quoted"],
    )
    assert msg_str(msg) == ".input {$var1}\n.local $var2 = {$var1}\n{{quoted}}"

    msg = mf2_parse_message(
        ".input {$var1} .local $var2 = {42 :number opt=$var1} {{quoted}}"
    )
    assert msg == PatternMessage(
        declarations={
            "var1": Expression(VariableRef("var1")),
            "var2": Expression("42", "number", {"opt": VariableRef("var1")}),
        },
        pattern=["quoted"],
    )
    assert (
        msg_str(msg)
        == ".input {$var1}\n.local $var2 = {42 :number opt=$var1}\n{{quoted}}"
    )

    fail(".local $var = {$var} {{quoted}}")
    fail(".input {$var} .input {$var} {{quoted}}")
    fail(".input {$var} .local $var = {42} {{quoted}}")
    fail(".local $var = {42} .input {$var} {{quoted}}")
    fail(".local $var1 = {$var2} .local $var2 = {42} {{quoted}}")

    msg = mf2_parse_message(
        ".input {$foo :string} .local $bar = {42 :number} {{Hello {$foo}{$bar}}}"
    )
    assert msg == PatternMessage(
        declarations={
            "foo": Expression(VariableRef("foo"), "string"),
            "bar": Expression("42", "number"),
        },
        pattern=[
            "Hello ",
            Expression(VariableRef("foo")),
            Expression(VariableRef("bar")),
        ],
    )
    assert (
        msg_str(msg)
        == ".input {$foo :string}\n.local $bar = {42 :number}\n"
        + "{{Hello {$foo}{$bar}}}"
    )


def test_select_message():
    msg = mf2_parse_message(".input{$foo :string}.match $foo *{{variant}}")
    assert msg == SelectMessage(
        declarations={"foo": Expression(VariableRef("foo"), "string")},
        selectors=(VariableRef("foo"),),
        variants={(CatchallKey(),): ["variant"]},
    )
    assert msg_str(msg) == ".input {$foo :string}\n.match $foo\n* {{variant}}"

    msg = mf2_parse_message(
        """
        .input {$var :string}
        .match $var
        key {{one}}
        * {{two}}
        """
    )
    assert msg == SelectMessage(
        declarations={"var": Expression(VariableRef("var"), "string")},
        selectors=(VariableRef("var"),),
        variants={("key",): ["one"], (CatchallKey(),): ["two"]},
    )
    assert msg_str(msg) == ".input {$var :string}\n.match $var\nkey {{one}}\n* {{two}}"

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

    msg = mf2_parse_message(
        """
        .input {$foo :string}
        .local $bar = {$foo}
        .match $foo $bar
        key |quoted key| {{one}}
        key |*| {{two}}
        * key {{three}}
        * * {{four}}
        """
    )
    assert msg == SelectMessage(
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
    )
    assert (
        msg_str(msg)
        == ".input {$foo :string}\n.local $bar = {$foo}\n.match $foo $bar\n"
        + "key |quoted key| {{one}}\n"
        + "key |*| {{two}}\n"
        + "* key {{three}}\n"
        + "* * {{four}}"
    )

    fail(".input {$foo} .match $foo key {{one}}").startswith("Missing fallback variant")

    fail(".input {$foo} .match $foo * {{one}}").startswith(
        "Missing selector annotation"
    )
