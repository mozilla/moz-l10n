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
from moz.l10n.message import parse_message
from moz.l10n.model import Expression, Markup, PatternMessage, VariableRef


class TestParseMessage(TestCase):
    def test_plain(self):
        msg = parse_message(Format.plain_json, "hello %% world")
        assert msg == PatternMessage(["hello %% world"])

    def test_printf(self):
        msg = parse_message(
            Format.plain_json, "hello %% world", printf_placeholders=True
        )
        assert msg == PatternMessage(
            ["hello ", Expression("%", attributes={"source": "%%"}), " world"]
        )

    def test_webext_numeric(self):
        msg = parse_message(Format.webext, "ph $1")
        assert msg == PatternMessage(
            ["ph ", Expression(VariableRef("arg1"), attributes={"source": "$1"})]
        )

    def test_webext_named_no_placeholders(self):
        with self.assertRaises(ValueError):
            parse_message(Format.webext, "ph $x$")

    def test_webext_named_with_placeholders(self):
        msg = parse_message(
            Format.webext, "ph $x$", webext_placeholders={"x": {"content": "$2"}}
        )
        assert msg == PatternMessage(
            declarations={
                "x": Expression(VariableRef("arg2"), attributes={"source": "$2"})
            },
            pattern=["ph ", Expression(VariableRef("x"), attributes={"source": "$x$"})],
        )

    def test_fluent(self):
        with self.assertRaises(UnsupportedFormat):
            parse_message(Format.fluent, "key = hello\n")


class TestParseXliffMessage(TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from moz.l10n.formats.xliff import xliff_parse_message  # noqa: F401
        except ImportError:
            raise SkipTest("Requires [xml] extra")

    def test_simple(self):
        msg = parse_message(Format.xliff, "Hello, <b>%s</b>")
        assert msg == PatternMessage(
            [
                "Hello, ",
                Markup(kind="open", name="b"),
                "%s",
                Markup(kind="close", name="b"),
            ]
        )

    def test_xcode(self):
        msg = parse_message(Format.xliff, "Hello, <b>%s</b>", xliff_is_xcode=True)
        assert msg == PatternMessage(
            [
                "Hello, ",
                Markup(kind="open", name="b"),
                Expression(VariableRef("str"), "string", attributes={"source": "%s"}),
                Markup(kind="close", name="b"),
            ]
        )

    def test_parse_error(self):
        with self.assertRaises(Exception):
            parse_message(Format.xliff, "Hello, <b>%s")


class TestParseAndroidMessage(TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from moz.l10n.formats.android import android_parse_message  # noqa: F401
        except ImportError:
            raise SkipTest("Requires [xml] extra")

    def test_placeholders(self):
        msg = parse_message(Format.android, "Hello, %1$s! You have %2$d new messages.")
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

    def test_markup(self):
        msg = parse_message(Format.android, "Welcome to <b>&foo;</b>&bar;!")
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
