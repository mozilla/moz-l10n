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
from moz.l10n.model import Comment, Entry, Metadata, PatternMessage, Resource, Section
from moz.l10n.resource import l10n_equal


class TestL10nEqual(TestCase):
    def test_equal(self):
        a = Resource(
            Format.fluent,
            [
                Section(
                    (),
                    [
                        Entry(
                            ("foo",),
                            PatternMessage(["Foo"]),
                            properties={"p": PatternMessage(["Prop"])},
                        )
                    ],
                )
            ],
        )
        b = Resource(
            Format.fluent,
            [
                Section(
                    (),
                    [
                        Entry(
                            ("foo",),
                            PatternMessage(["Foo"]),
                            properties={"p": PatternMessage(["Prop"])},
                        )
                    ],
                )
            ],
        )
        assert l10n_equal(a, b)

    def test_not_equal_formats(self):
        a = Resource(Format.inc, [Section((), [Entry(("foo",), "Foo")])])
        b = Resource(Format.ini, [Section((), [Entry(("foo",), "Foo")])])
        assert not l10n_equal(a, b)

    def test_not_equal_entry_values(self):
        a = Resource(None, [Section((), [Entry(("foo",), "Foo 1")])])
        b = Resource(None, [Section((), [Entry(("foo",), "Foo 2")])])
        assert not l10n_equal(a, b)

    def test_not_equal_entry_comments(self):
        a = Resource(None, [Section((), [Entry(("foo",), "Foo", comment="Bar 1")])])
        b = Resource(None, [Section((), [Entry(("foo",), "Foo", comment="Bar 2")])])
        assert not l10n_equal(a, b)

    def test_equal_stripped_entry_comments(self):
        a = Resource(None, [Section((), [Entry(("foo",), "Foo", comment="Bar 1")])])
        b = Resource(None, [Section((), [Entry(("foo",), "Foo", comment="Bar 1   ")])])
        assert l10n_equal(a, b)

    def test_not_equal_entry_meta(self):
        a = Resource(
            None,
            [Section((), [Entry(("foo",), "Foo", meta=[Metadata("key", "Bar 1")])])],
        )
        b = Resource(
            None,
            [Section((), [Entry(("foo",), "Foo", meta=[Metadata("key", "Bar 2")])])],
        )
        assert not l10n_equal(a, b)

    def test_not_equal_entry_properties(self):
        a = Resource(
            None,
            [Section((), [Entry(("foo",), "Foo")])],
        )
        b = Resource(
            None,
            [Section((), [Entry(("foo",), "Foo", properties={"p": "Prop"})])],
        )
        c = Resource(
            None,
            [Section((), [Entry(("foo",), "Foo", properties={"p": "Prop 2"})])],
        )
        assert l10n_equal(b, b)
        assert not l10n_equal(a, b)
        assert not l10n_equal(b, c)

    def test_not_equal_section_ids(self):
        a = Resource(None, [Section(("a",), [Entry(("foo",), "Foo")])])
        b = Resource(None, [Section(("b",), [Entry(("foo",), "Foo")])])
        assert not l10n_equal(a, b)

    def test_not_equal_section_comments(self):
        a = Resource(None, [Section((), [Entry(("foo",), "Foo")])])
        b = Resource(None, [Section((), [Entry(("foo",), "Foo")], "Bar")])
        assert not l10n_equal(a, b)

    def test_equal_stripped_section_comments(self):
        a = Resource(None, [Section((), [Entry(("foo",), "Foo")], "\nBar")])
        b = Resource(None, [Section((), [Entry(("foo",), "Foo")], "Bar")])
        assert l10n_equal(a, b)

    def test_ignore_non_l10n(self):
        a = Resource(None, [Section((), []), Section((), [Entry(("foo",), "Foo")])])
        b = Resource(None, [Section((), [Entry(("foo",), "Foo"), Comment("Bar")])])
        assert l10n_equal(a, b)

    def test_reorder_entries(self):
        a = Resource(
            None, [Section((), [Entry(("foo",), "Foo"), Entry(("bar",), "Bar")])]
        )
        b = Resource(
            None, [Section((), [Entry(("bar",), "Bar"), Entry(("foo",), "Foo")])]
        )
        assert l10n_equal(a, b)

    def test_reorder_meta(self):
        am = [Metadata("a", "A1"), Metadata("a", "A2"), Metadata("b", "B")]
        bm = [Metadata("b", "B"), Metadata("a", "A2"), Metadata("a", "A1")]
        a = Resource(None, [Section((), [Entry(("foo",), "Foo", meta=am)])])
        b = Resource(None, [Section((), [Entry(("foo",), "Foo", meta=bm)])])
        assert l10n_equal(a, b)

    def test_empty_sections(self):
        a = Resource(
            None, [Section((), [Entry(("foo",), "Foo"), Entry(("bar",), "Bar")])]
        )
        b = Resource(
            None,
            [
                Section((), [Entry(("bar",), "Bar")]),
                Section((), [Entry(("foo",), "Foo")]),
            ],
        )
        assert l10n_equal(a, b)
