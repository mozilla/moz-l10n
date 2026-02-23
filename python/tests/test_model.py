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

from unittest import TestCase

from moz.l10n.formats import Format
from moz.l10n.model import (
    CatchallKey,
    Comment,
    Entry,
    Expression,
    Metadata,
    PatternMessage,
    Resource,
    Section,
    SelectMessage,
)


class TestMessage(TestCase):
    def test_is_empty(self):
        assert PatternMessage([]).is_empty()
        assert PatternMessage([""]).is_empty()
        assert PatternMessage(["", ""]).is_empty()
        assert not PatternMessage(["x"]).is_empty()
        assert not PatternMessage(["", "x"]).is_empty()
        assert not PatternMessage([Expression("")]).is_empty()

        assert SelectMessage(
            declarations={},
            selectors=(),
            variants={
                ("x",): [],
                ("y",): [""],
                (CatchallKey(),): ["", ""],
            },
        ).is_empty()
        assert not SelectMessage(
            declarations={},
            selectors=(),
            variants={
                ("x",): [],
                ("y",): [""],
                (CatchallKey(),): ["", Expression("")],
            },
        ).is_empty()


class TestResource(TestCase):
    def test_all_entries_some(self):
        entries = [
            Entry(("e0",), PatternMessage(["m0"])),
            Entry(("e1",), PatternMessage(["m1"])),
            Entry(("e2",), PatternMessage(["m2"])),
            Entry(("e3",), PatternMessage(["m3"])),
        ]
        res = Resource(
            Format.inc,
            [
                Section((), [Comment("c1"), entries[0], Comment("c2"), entries[1]]),
                Section(("a",), [entries[2], Comment("c3"), entries[3], Comment("c4")]),
            ],
        )
        assert list(res.all_entries()) == entries
        assert (
            repr(res)
            == "Resource(Format.inc,[Section((),[Comment('c1'), "
            + "Entry(('e0',),PatternMessage(['m0'])), Comment('c2'), "
            + "Entry(('e1',),PatternMessage(['m1']))]), "
            + "Section(('a',),[Entry(('e2',),PatternMessage(['m2'])), Comment('c3'), "
            + "Entry(('e3',),PatternMessage(['m3'])), Comment('c4')])])"
        )

    def test_all_entries_none(self):
        res = Resource(
            Format.inc,
            [
                Section((), [Comment("c1"), Comment("c2")]),
                Section(("a",), [Comment("c3"), Comment("c4")]),
            ],
        )
        assert next(res.all_entries(), None) is None
        assert (
            repr(res)
            == "Resource(Format.inc,[Section((),[Comment('c1'), Comment('c2')]), "
            + "Section(('a',),[Comment('c3'), Comment('c4')])])"
        )


class TestMeta(TestCase):
    def test_entry(self):
        entry = Entry(
            ("e0",),
            PatternMessage(["m0"]),
            meta=[Metadata("key", "value1"), Metadata("key", "value2")],
        )
        assert entry.get_meta("key") == "value1"
        assert entry.get_meta("foo") is None

        assert entry.has_meta("key")
        assert entry.has_meta("key", "value2")
        assert not entry.get_meta("foo")
        assert not entry.has_meta("key", "set value")

        entry.set_meta("foo", "bar")
        entry.set_meta("key", "set value")

        assert entry.meta == [
            Metadata("key", "set value"),
            Metadata("key", "value2"),
            Metadata("foo", "bar"),
        ]

        assert entry.del_meta("key") == 2
        assert entry.del_meta("bar") == 0
        assert entry.meta == [Metadata("foo", "bar")]
        assert (
            repr(entry)
            == "Entry(('e0',),meta=[Metadata('foo','bar')],value=PatternMessage(['m0']))"
        )

    def test_resource(self):
        res = Resource(
            Format.properties,
            [Section((), [])],
            meta=[Metadata("key", "value1"), Metadata("key", "value2")],
        )

        assert res.get_meta("key") == "value1"
        assert res.get_meta("foo") is None

        res.set_meta("foo", "bar")
        res.set_meta("key", "set value")

        assert res.meta == [
            Metadata("key", "set value"),
            Metadata("key", "value2"),
            Metadata("foo", "bar"),
        ]

        assert res.del_meta("key") == 2
        assert res.del_meta("bar") == 0
        assert res.meta == [Metadata("foo", "bar")]
        assert (
            repr(res)
            == "Resource(Format.properties,meta=[Metadata('foo','bar')],sections=[Section((),[])])"
        )
