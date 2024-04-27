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

from importlib.resources import files
from textwrap import dedent
from unittest import TestCase

from moz.l10n.resource.data import Entry, Resource, Section
from moz.l10n.resource.plain_json import plain_json_parse, plain_json_serialize

# Show full diff in self.assertEqual. https://stackoverflow.com/a/61345284
# __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

source = files("tests.data").joinpath("messages.json").read_bytes()


class TestPlain(TestCase):
    def test_parse(self):
        res = plain_json_parse(source)
        self.assertEqual(
            res,
            Resource(
                [
                    Section(
                        [],
                        [
                            Entry(["SourceString", "message"], "Translated String"),
                            Entry(["SourceString", "description"], "Sample comment"),
                            Entry(
                                ["MultipleComments", "message"],
                                "Translated Multiple Comments",
                            ),
                            Entry(
                                ["MultipleComments", "description"], "Second comment"
                            ),
                            Entry(
                                ["NoCommentsorSources", "message"],
                                "Translated No Comments or Sources",
                            ),
                            Entry(
                                ["placeholders", "message"],
                                "Hello$$$ $1YOUR_NAME$ at $2",
                            ),
                            Entry(["placeholders", "description"], "Peer greeting"),
                            Entry(
                                [
                                    "placeholders",
                                    "placeholders",
                                    "1your_name",
                                    "content",
                                ],
                                "$1",
                            ),
                            Entry(
                                [
                                    "placeholders",
                                    "placeholders",
                                    "1your_name",
                                    "example",
                                ],
                                "Cira",
                            ),
                            Entry(["repeated_ref", "message"], "$foo$ and $Foo$"),
                            Entry(
                                ["repeated_ref", "placeholders", "foo", "content"], "$1"
                            ),
                        ],
                    )
                ],
            ),
        )

    def test_serialize(self):
        res = plain_json_parse(source)
        self.assertEqual(
            "".join(plain_json_serialize(res)),
            dedent(
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
            ),
        )
