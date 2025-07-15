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

from unittest import SkipTest, TestCase

from moz.l10n.formats import Format, UnsupportedFormat
from moz.l10n.message import parse_message, serialize_message
from moz.l10n.model import Expression, Markup, PatternMessage, VariableRef


class TestMessage(TestCase):
    def test_plain(self):
        src = "hello %% world"
        msg = parse_message(Format.plain_json, src)
        assert msg == PatternMessage([src])
        res = serialize_message(Format.plain_json, msg)
        assert res == src

    def test_printf(self):
        src = "hello %% world"
        msg = parse_message(Format.plain_json, src, printf_placeholders=True)
        assert msg == PatternMessage(
            ["hello ", Expression("%", attributes={"source": "%%"}), " world"]
        )
        res = serialize_message(Format.plain_json, msg)
        assert res == src

    def test_properties_printf(self):
        src = "hello %% world"
        msg = parse_message(Format.properties, src, printf_placeholders=True)
        assert msg == PatternMessage(
            ["hello ", Expression("%", attributes={"source": "%%"}), " world"]
        )
        res = serialize_message(Format.properties, msg)
        assert res == src

    def test_webext_numeric(self):
        src = "ph $1"
        msg = parse_message(Format.webext, src)
        assert msg == PatternMessage(
            ["ph ", Expression(VariableRef("arg1"), attributes={"source": "$1"})]
        )
        res = serialize_message(Format.webext, msg)
        assert res == src

    def test_webext_named_no_placeholders(self):
        with self.assertRaises(ValueError):
            parse_message(Format.webext, "ph $x$")

    def test_webext_named_with_placeholders(self):
        src = "ph $x$"
        msg = parse_message(
            Format.webext, src, webext_placeholders={"x": {"content": "$2"}}
        )
        assert msg == PatternMessage(
            declarations={
                "x": Expression(VariableRef("arg2"), attributes={"source": "$2"})
            },
            pattern=["ph ", Expression(VariableRef("x"), attributes={"source": "$x$"})],
        )
        res = serialize_message(Format.webext, msg)
        assert res == src

    def test_fluent(self):
        msg = parse_message(Format.fluent, "hello { $world }")
        assert msg == PatternMessage(["hello ", Expression(VariableRef("world"))])
        res = serialize_message(Format.fluent, msg)
        assert res == "hello { $world }"


class TestUnsupportedFormat(TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from moz.l10n.formats.xliff import xliff_parse_message  # noqa: F401

            raise SkipTest("Requires not having [xml] extra")
        except ImportError:
            pass

    def test_exception(self):
        with self.assertRaises(UnsupportedFormat):
            parse_message(Format.xliff, "")
        with self.assertRaises(UnsupportedFormat):
            serialize_message(Format.xliff, PatternMessage([]))


class TestXliffMessage(TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from moz.l10n.formats.xliff import xliff_parse_message  # noqa: F401
        except ImportError:
            raise SkipTest("Requires [xml] extra")

    def test_simple(self):
        src = "Hello, <b>%s</b>"
        msg = parse_message(Format.xliff, src)
        assert msg == PatternMessage(
            [
                "Hello, ",
                Markup(kind="open", name="b"),
                "%s",
                Markup(kind="close", name="b"),
            ]
        )
        res = serialize_message(Format.xliff, msg)
        assert res == src

    def test_xcode(self):
        src = "Hello, <b>%s</b>"
        msg = parse_message(Format.xliff, src, xliff_is_xcode=True)
        assert msg == PatternMessage(
            [
                "Hello, ",
                Markup(kind="open", name="b"),
                Expression(VariableRef("str"), "string", attributes={"source": "%s"}),
                Markup(kind="close", name="b"),
            ]
        )
        res = serialize_message(Format.xliff, msg)
        assert res == src

    def test_parse_error(self):
        with self.assertRaises(Exception):
            parse_message(Format.xliff, "Hello, <b>%s")


class TestAndroidMessage(TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from moz.l10n.formats.android import android_parse_message  # noqa: F401
        except ImportError:
            raise SkipTest("Requires [xml] extra")

    def test_placeholders(self):
        src = "Hello, %1$s! You have %2$d new messages."
        msg = parse_message(Format.android, src)
        assert msg == PatternMessage(
            [
                "Hello, ",
                Expression(
                    VariableRef("arg1"), "string", attributes={"source": "%1$s"}
                ),
                "! You have ",
                Expression(
                    VariableRef("arg2"), "integer", attributes={"source": "%2$d"}
                ),
                " new messages.",
            ]
        )
        res = serialize_message(Format.android, msg)
        assert res == src

    def test_markup(self):
        src = "Welcome to <b>&foo;</b>&bar;!"
        msg = parse_message(Format.android, src)
        assert msg == PatternMessage(
            [
                "Welcome to ",
                Markup("open", "b"),
                Expression(VariableRef("foo"), "entity"),
                Markup("close", "b"),
                Expression(VariableRef("bar"), "entity"),
                "!",
            ]
        )
        res = serialize_message(Format.android, msg)
        assert res == src

    def test_spaces(self):
        src = "One\ttwo\xa0three\\u00a0four"

        msg = parse_message(Format.android, src)
        assert msg == PatternMessage(["One two three\xa0four"])
        res = serialize_message(Format.android, msg)
        assert res == "One two three\\u00a0four"

        msg = parse_message(Format.android, src, android_ascii_spaces=True)
        assert msg == PatternMessage(["One two\xa0three\xa0four"])
        res = serialize_message(Format.android, msg)
        assert res == "One two\\u00a0three\\u00a0four"
