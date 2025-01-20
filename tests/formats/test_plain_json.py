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

from moz.l10n.formats import Format
from moz.l10n.formats.plain_json import plain_json_parse, plain_json_serialize
from moz.l10n.message.data import PatternMessage
from moz.l10n.resource.data import Entry, Resource, Section

source = files("tests.formats.data").joinpath("messages.json").read_bytes()


class TestPlain(TestCase):
    def test_parse(self):
        res = plain_json_parse(source)
        assert res == Resource(
            Format.plain_json,
            [
                Section(
                    (),
                    [
                        Entry(
                            ("SourceString", "message"),
                            PatternMessage(["Translated String"]),
                        ),
                        Entry(
                            ("SourceString", "description"),
                            PatternMessage(["Sample comment"]),
                        ),
                        Entry(
                            ("MultipleComments", "message"),
                            PatternMessage(["Translated Multiple Comments"]),
                        ),
                        Entry(
                            ("MultipleComments", "description"),
                            PatternMessage(["Second comment"]),
                        ),
                        Entry(
                            ("NoCommentsorSources", "message"),
                            PatternMessage(["Translated No Comments or Sources"]),
                        ),
                        Entry(
                            ("placeholders", "message"),
                            PatternMessage(["Hello$$$ $1YOUR_NAME$ at $2"]),
                        ),
                        Entry(
                            ("placeholders", "description"),
                            PatternMessage(["Peer greeting"]),
                        ),
                        Entry(
                            (
                                "placeholders",
                                "placeholders",
                                "1your_name",
                                "content",
                            ),
                            PatternMessage(["$1"]),
                        ),
                        Entry(
                            (
                                "placeholders",
                                "placeholders",
                                "1your_name",
                                "example",
                            ),
                            PatternMessage(["Cira"]),
                        ),
                        Entry(
                            ("repeated_ref", "message"),
                            PatternMessage(["$foo$ and $Foo$"]),
                        ),
                        Entry(
                            ("repeated_ref", "placeholders", "foo", "content"),
                            PatternMessage(["$1"]),
                        ),
                    ],
                )
            ],
        )

    def test_serialize(self):
        res = plain_json_parse(source)
        assert "".join(plain_json_serialize(res)) == dedent(
            """\
            {
              "SourceString": {
                "message": "Translated String",
                "description": "Sample comment"
              },
              "MultipleComments": {
                "message": "Translated Multiple Comments",
                "description": "Second comment"
              },
              "NoCommentsorSources": {
                "message": "Translated No Comments or Sources"
              },
              "placeholders": {
                "message": "Hello$$$ $1YOUR_NAME$ at $2",
                "description": "Peer greeting",
                "placeholders": {
                  "1your_name": {
                    "content": "$1",
                    "example": "Cira"
                  }
                }
              },
              "repeated_ref": {
                "message": "$foo$ and $Foo$",
                "placeholders": {
                  "foo": {
                    "content": "$1"
                  }
                }
              }
            }
            """
        )
