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

from moz.l10n.resource import add_entries
from moz.l10n.resource.data import Entry, Resource, Section


class TestAddEntries(TestCase):
    def test_no_changes(self):
        target = Resource(None, [Section((), [Entry(("foo",), "Foo")])])
        source = Resource(None, [Section((), [Entry(("foo",), "Foo")])])
        self.assertEqual(add_entries(target, source), 0)
        self.assertEqual(
            target, Resource(None, [Section((), [Entry(("foo",), "Foo")])])
        )

    def test_message_changed_in_source(self):
        target = Resource(None, [Section((), [Entry(("foo",), "Foo 1")])])
        source = Resource(None, [Section((), [Entry(("foo",), "Foo 2")])])
        self.assertEqual(add_entries(target, source), 0)
        self.assertEqual(
            target, Resource(None, [Section((), [Entry(("foo",), "Foo 1")])])
        )

    def test_message_changed_in_source_use_source_entries(self):
        target = Resource(None, [Section((), [Entry(("foo",), "Foo 1")])])
        source = Resource(None, [Section((), [Entry(("foo",), "Foo 2")])])
        assert add_entries(target, source, use_source_entries=True) == 1
        assert target == Resource(None, [Section((), [Entry(("foo",), "Foo 2")])])

    def test_message_comment_changed_in_source_use_source_entries(self):
        target = Resource(None, [Section((), [Entry(("foo",), "Foo", "Bar 1")])])
        source = Resource(None, [Section((), [Entry(("foo",), "Foo", "Bar 2")])])
        assert add_entries(target, source, use_source_entries=True) == 1
        assert target == Resource(
            None, [Section((), [Entry(("foo",), "Foo", "Bar 2")])]
        )

    def test_message_not_in_source(self):
        target = Resource(
            None, [Section((), [Entry(("foo",), "Foo 1"), Entry(("bar",), "Bar 1")])]
        )
        source = Resource(None, [Section((), [Entry(("foo",), "Foo 2")])])
        self.assertEqual(add_entries(target, source), 0)
        self.assertEqual(
            target,
            Resource(
                None,
                [Section((), [Entry(("foo",), "Foo 1"), Entry(("bar",), "Bar 1")])],
            ),
        )

    def test_message_added_in_source(self):
        target = Resource(None, [Section((), [Entry(("foo",), "Foo 1")])])
        source = Resource(
            None, [Section((), [Entry(("foo",), "Foo 2"), Entry(("bar",), "Bar 2")])]
        )
        self.assertEqual(add_entries(target, source), 1)
        self.assertEqual(
            target,
            Resource(
                None,
                [Section((), [Entry(("foo",), "Foo 1"), Entry(("bar",), "Bar 2")])],
            ),
        )

    def test_messages_reordered(self):
        target = Resource(
            None, [Section((), [Entry(("foo",), "Foo 1"), Entry(("bar",), "Bar 1")])]
        )
        source = Resource(
            None, [Section((), [Entry(("bar",), "Bar 2"), Entry(("foo",), "Foo 2")])]
        )
        assert add_entries(target, source) == 0
        assert target == Resource(
            None,
            [Section((), [Entry(("foo",), "Foo 1"), Entry(("bar",), "Bar 1")])],
        )
        assert add_entries(target, source, use_source_entries=True) == 2
        assert target == Resource(
            None,
            [Section((), [Entry(("foo",), "Foo 2"), Entry(("bar",), "Bar 2")])],
        )

    def test_message_addition_order(self):
        target = Resource(
            None, [Section((), [Entry(("foo",), "Foo 1"), Entry(("bar",), "Bar 1")])]
        )
        source_entries = [
            Entry(("bar",), "Bar 2"),
            Entry(("x",), "X"),
            Entry(("foo",), "Foo 2"),
            Entry(("y",), "Y"),
        ]
        source = Resource(None, [Section((), source_entries)])
        self.assertEqual(add_entries(target, source), 2)
        exp_entries = [
            Entry(("foo",), "Foo 1"),
            Entry(("y",), "Y"),
            Entry(("bar",), "Bar 1"),
            Entry(("x",), "X"),
        ]
        self.assertEqual(target, Resource(None, [Section((), exp_entries)]))

    def test_added_sections(self):
        target = Resource(
            None,
            [Section(("1",), [Entry(("foo",), "Foo 1"), Entry(("bar",), "Bar 1")])],
        )
        source = Resource(
            None,
            [
                Section(("0",), [Entry(("x",), "X")]),
                Section(("1",), [Entry(("foo",), "Foo 2"), Entry(("bar",), "Bar 2")]),
                Section(("2",), [Entry(("x",), "Y")]),
            ],
        )
        self.assertEqual(add_entries(target, source), 2)
        self.assertEqual(
            target,
            Resource(
                None,
                [
                    Section(("0",), [Entry(("x",), "X")]),
                    Section(
                        ("1",), [Entry(("foo",), "Foo 1"), Entry(("bar",), "Bar 1")]
                    ),
                    Section(("2",), [Entry(("x",), "Y")]),
                ],
            ),
        )

    def test_anon_sections(self):
        target = Resource(
            None,
            [
                Section((), [Entry(("foo",), "Foo 1")], "C1"),
                Section((), [Entry(("bar",), "Bar 1")], "C2"),
            ],
        )
        source = Resource(
            None,
            [
                Section((), [Entry(("x",), "X")], "C0"),
                Section((), [Entry(("y",), "Y")], "C2"),
                Section((), [Entry(("z",), "Z")], "C1"),
            ],
        )
        self.assertEqual(add_entries(target, source), 3)
        self.assertEqual(
            target,
            Resource(
                None,
                [
                    Section((), [Entry(("x",), "X")], "C0"),
                    Section((), [Entry(("foo",), "Foo 1"), Entry(("z",), "Z")], "C1"),
                    Section((), [Entry(("bar",), "Bar 1"), Entry(("y",), "Y")], "C2"),
                ],
            ),
        )
