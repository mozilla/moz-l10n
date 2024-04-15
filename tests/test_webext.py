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

from moz.l10n.message import Declaration, Expression, PatternMessage, VariableRef
from moz.l10n.resource import Entry, Resource, Section
from moz.l10n.webext import webext_parse, webext_serialize

# Show full diff in self.assertEqual. https://stackoverflow.com/a/61345284
# __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

source = files("tests.data").joinpath("messages.json").read_bytes()


class TestWebext(TestCase):
    def test_parse(self):
        res = webext_parse(source)
        self.assertEqual(
            res,
            Resource(
                [
                    Section(
                        [],
                        [
                            Entry(
                                ["SourceString"],
                                PatternMessage(["Translated String"]),
                                comment="Sample comment",
                            ),
                            Entry(
                                ["MultipleComments"],
                                PatternMessage(["Translated Multiple Comments"]),
                                comment="Second comment",
                            ),
                            Entry(
                                ["NoCommentsorSources"],
                                PatternMessage(["Translated No Comments or Sources"]),
                            ),
                            Entry(
                                ["placeholders"],
                                PatternMessage(
                                    [
                                        "Hello$$ ",
                                        Expression(VariableRef("1YOUR_NAME")),
                                        " at ",
                                        Expression(VariableRef("$2")),
                                    ],
                                    declarations=[
                                        Declaration(
                                            "1YOUR_NAME",
                                            Expression(
                                                VariableRef("$1"),
                                                attributes={"example": "Cira"},
                                            ),
                                        )
                                    ],
                                ),
                                comment="Peer greeting",
                            ),
                            Entry(
                                ["repeated_ref"],
                                PatternMessage(
                                    [
                                        Expression(VariableRef("foo")),
                                        " and ",
                                        Expression(VariableRef("foo")),
                                    ],
                                    declarations=[
                                        Declaration(
                                            "foo", Expression(VariableRef("$1"))
                                        )
                                    ],
                                ),
                            ),
                        ],
                    )
                ],
            ),
        )

    def test_serialize(self):
        res = webext_parse(source)
        self.assertEqual(
            "".join(webext_serialize(res)),
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
                      "1YOUR_NAME": {
                        "content": "$1",
                        "example": "Cira"
                      }
                    }
                  },
                  "repeated_ref": {
                    "message": "$foo$ and $foo$",
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

    def test_trim_comments(self):
        res = webext_parse(source)
        self.assertEqual(
            "".join(webext_serialize(res, trim_comments=True)),
            dedent(
                """\
                {
                  "SourceString": {
                    "message": "Translated String"
                  },
                  "MultipleComments": {
                    "message": "Translated Multiple Comments"
                  },
                  "NoCommentsorSources": {
                    "message": "Translated No Comments or Sources"
                  },
                  "placeholders": {
                    "message": "Hello$$$ $1YOUR_NAME$ at $2",
                    "placeholders": {
                      "1YOUR_NAME": {
                        "content": "$1"
                      }
                    }
                  },
                  "repeated_ref": {
                    "message": "$foo$ and $foo$",
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
