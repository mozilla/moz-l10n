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

from json import load
from os.path import dirname
from pathlib import Path
from unittest import TestCase

from jsonschema import Draft7Validator, ValidationError
from moz.l10n.message import entry_from_json, entry_to_json
from moz.l10n.model import (
    CatchallKey,
    Entry,
    Expression,
    Metadata,
    PatternMessage,
    SelectMessage,
    VariableRef,
)
from referencing import Registry

schemas = Path(dirname(__file__)) / "../../schemas"
msg_registry = Registry().with_contents(
    [("./message.json", load((schemas / "message.json").open()))]
)
validator = Draft7Validator(
    load((schemas / "entry.json").open()), registry=msg_registry
)


class TestEntryJSON(TestCase):
    def test_empty(self):
        entry = Entry(("key",), PatternMessage([]))
        id, json = entry_to_json(entry)
        assert json == {"=": []}
        validator.validate(json)
        assert entry_from_json(id, json) == entry

    def test_pattern(self):
        entry = Entry(("key",), PatternMessage(["message"]))
        id, json = entry_to_json(entry)
        assert json == {"=": ["message"]}
        validator.validate(json)
        assert entry_from_json(id, json) == entry

    def test_validation_error(self):
        json = {"=": ["message", {"x": "invalid"}]}
        with self.assertRaises(ValidationError):
            validator.validate(json)

    def test_comments_and_meta(self):
        entry = Entry(
            id=("key",),
            comment="entry comment",
            meta=[Metadata("key", "value 1"), Metadata("key", "value 2")],
            value=PatternMessage(["message"]),
            properties={"prop": PatternMessage(["prop value"])},
        )
        id, json = entry_to_json(entry)
        assert json == {
            "#": "entry comment",
            "@": [["key", "value 1"], ["key", "value 2"]],
            "=": ["message"],
            "+": {"prop": ["prop value"]},
        }
        validator.validate(json)
        assert entry_from_json(id, json) == entry

    def test_select(self):
        entry = Entry(
            ("ks",),
            SelectMessage(
                declarations={"x": Expression("y")},
                selectors=(VariableRef("x"),),
                variants={(CatchallKey(),): ["ms"]},
            ),
        )
        id, json = entry_to_json(entry)
        assert json == {
            "=": {
                "alt": [{"keys": [{"*": ""}], "pat": ["ms"]}],
                "decl": {"x": {"_": "y"}},
                "sel": ["x"],
            }
        }
        validator.validate(json)
        assert entry_from_json(id, json) == entry

    def test_multipart_key(self):
        entry = Entry(("a", "b.c"), PatternMessage(["message"]))
        id, json = entry_to_json(entry)
        assert id == "a.b\\.c"
        assert entry_from_json(id, json) == entry
