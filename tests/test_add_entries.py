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
        target = Resource(None, [Section((), [Entry(("id",), "msg")])])
        source = Resource(None, [Section((), [Entry(("id",), "msg")])])
        assert add_entries(target, source) == 0
        assert target == Resource(None, [Section((), [Entry(("id",), "msg")])])

    def test_message_changed_in_source(self):
        target = Resource(None, [Section((), [Entry(("id",), "msg 1")])])
        source = Resource(None, [Section((), [Entry(("id",), "msg 2")])])
        assert add_entries(target, source) == 0
        assert target == Resource(None, [Section((), [Entry(("id",), "msg 1")])])

    def test_message_changed_in_source_use_source_entries(self):
        target = Resource(None, [Section((), [Entry(("id",), "msg 1")])])
        source = Resource(None, [Section((), [Entry(("id",), "msg 2")])])
        assert add_entries(target, source, use_source_entries=True) == 1
        assert target == Resource(None, [Section((), [Entry(("id",), "msg 2")])])

    def test_message_comment_changed_in_source(self):
        target = Resource(None, [Section((), [Entry(("id",), "msg", "Comment 1")])])
        source = Resource(None, [Section((), [Entry(("id",), "msg", "Comment 2")])])
        assert add_entries(target, source) == 0
        assert target == Resource(
            None, [Section((), [Entry(("id",), "msg", "Comment 1")])]
        )

    def test_message_comment_changed_in_source_use_source_entries(self):
        target = Resource(None, [Section((), [Entry(("id",), "msg", "Comment 1")])])
        source = Resource(None, [Section((), [Entry(("id",), "msg", "Comment 2")])])
        assert add_entries(target, source, use_source_entries=True) == 1
        assert target == Resource(
            None, [Section((), [Entry(("id",), "msg", "Comment 2")])]
        )

    def test_message_not_in_source(self):
        target = Resource(
            None,
            [Section((), [Entry(("id-1",), "msg 1A"), Entry(("id-2",), "msg 2A")])],
        )
        source = Resource(None, [Section((), [Entry(("id-1",), "msg 1B")])])
        assert add_entries(target, source) == 0
        assert target == Resource(
            None,
            [Section((), [Entry(("id-1",), "msg 1A"), Entry(("id-2",), "msg 2A")])],
        )

    def test_message_added_in_source(self):
        target = Resource(None, [Section((), [Entry(("id-1",), "msg 1A")])])
        source = Resource(
            None,
            [Section((), [Entry(("id-1",), "msg 1B"), Entry(("id-2",), "msg 2B")])],
        )
        assert add_entries(target, source) == 1
        assert target == Resource(
            None,
            [Section((), [Entry(("id-1",), "msg 1A"), Entry(("id-2",), "msg 2B")])],
        )

    def test_messages_reordered(self):
        target = Resource(
            None,
            [Section((), [Entry(("id-1",), "msg 1A"), Entry(("id-2",), "msg 2A")])],
        )
        source = Resource(
            None,
            [Section((), [Entry(("id-2",), "msg 2B"), Entry(("id-1",), "msg 1B")])],
        )
        assert add_entries(target, source) == 0
        assert target == Resource(
            None,
            [Section((), [Entry(("id-1",), "msg 1A"), Entry(("id-2",), "msg 2A")])],
        )

    def test_messages_reordered_use_source_entries(self):
        target = Resource(
            None,
            [Section((), [Entry(("id-1",), "msg 1A"), Entry(("id-2",), "msg 2A")])],
        )
        source = Resource(
            None,
            [Section((), [Entry(("id-2",), "msg 2B"), Entry(("id-1",), "msg 1B")])],
        )
        assert add_entries(target, source, use_source_entries=True) == 2
        assert target == Resource(
            None,
            [Section((), [Entry(("id-1",), "msg 1B"), Entry(("id-2",), "msg 2B")])],
        )

    def test_message_addition_order(self):
        target = Resource(
            None,
            [Section((), [Entry(("id-1",), "msg 1A"), Entry(("id-2",), "msg 2A")])],
        )
        source_entries = [
            Entry(("id-2",), "msg 2B"),
            Entry(("id-x",), "msg X"),
            Entry(("id-1",), "msg 1B"),
            Entry(("id-y",), "msg Y"),
        ]
        source = Resource(None, [Section((), source_entries)])
        assert add_entries(target, source) == 2
        exp_entries = [
            Entry(("id-1",), "msg 1A"),
            Entry(("id-y",), "msg Y"),
            Entry(("id-2",), "msg 2A"),
            Entry(("id-x",), "msg X"),
        ]
        assert target == Resource(None, [Section((), exp_entries)])

    def test_added_sections(self):
        target = Resource(
            None,
            [Section(("1",), [Entry(("id-1",), "msg 1A"), Entry(("id-2",), "msg 2A")])],
        )
        source = Resource(
            None,
            [
                Section(("0",), [Entry(("id-x",), "msg X")]),
                Section(
                    ("1",), [Entry(("id-1",), "msg 1B"), Entry(("id-2",), "msg 2B")]
                ),
                Section(("2",), [Entry(("id-x",), "msg Y")]),
            ],
        )
        assert add_entries(target, source) == 2
        assert target == Resource(
            None,
            [
                Section(("0",), [Entry(("id-x",), "msg X")]),
                Section(
                    ("1",), [Entry(("id-1",), "msg 1A"), Entry(("id-2",), "msg 2A")]
                ),
                Section(("2",), [Entry(("id-x",), "msg Y")]),
            ],
        )

    def test_anon_sections(self):
        target = Resource(
            None,
            [
                Section((), [Entry(("id-1",), "msg 1")], "Section Comment A"),
                Section((), [Entry(("id-2",), "msg 2")], "Section Comment B"),
            ],
        )
        source = Resource(
            None,
            [
                Section((), [Entry(("id-x",), "msg X")], "Section Comment C"),
                Section((), [Entry(("id-y",), "msg Y")], "Section Comment B"),
                Section((), [Entry(("id-z",), "msg Z")], "Section Comment A"),
            ],
        )
        assert add_entries(target, source) == 3
        assert target == Resource(
            None,
            [
                Section((), [Entry(("id-x",), "msg X")], "Section Comment C"),
                Section(
                    (),
                    [Entry(("id-1",), "msg 1"), Entry(("id-z",), "msg Z")],
                    "Section Comment A",
                ),
                Section(
                    (),
                    [Entry(("id-2",), "msg 2"), Entry(("id-y",), "msg Y")],
                    "Section Comment B",
                ),
            ],
        )
