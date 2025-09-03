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
    VariableRef,
)
from moz.l10n.resource import resource_from_json, resource_to_json
from referencing import Registry

schemas = Path(dirname(__file__)) / "../../schemas"
msg_registry = Registry().with_contents(
    [
        ("./message.json", load((schemas / "message.json").open())),
        ("./entry.json", load((schemas / "entry.json").open())),
    ]
)
validator = Draft7Validator(
    load((schemas / "resource.json").open()), registry=msg_registry
)


class TestMessage(TestCase):
    def test_empty(self):
        res = Resource(Format.properties, [])
        json = resource_to_json(res)
        assert json == {"fmt": "properties", "*": []}
        validator.validate(json)
        assert resource_from_json(json) == res
        with self.assertRaises(ValidationError):
            validator.validate({})

    def test_pattern(self):
        res = Resource(
            None, [Section((), [Entry(("key",), PatternMessage(["message"]))])]
        )
        json = resource_to_json(res)
        assert json == {"*": [{"~": {"key": {"=": ["message"]}}}]}
        validator.validate(json)
        assert resource_from_json(json) == res

        json = {"*": [{"~": {"key": {"=": ["message", {"x": "invalid"}]}}}]}
        with self.assertRaises(ValidationError):
            validator.validate(json)

    def test_comments_and_meta(self):
        res = Resource(
            format=None,
            comment="res comment",
            meta=[Metadata("key", "value")],
            sections=[
                Section(
                    id=(),
                    comment="section comment",
                    meta=[Metadata("key", "value 1"), Metadata("key", "value 2")],
                    entries=[
                        Entry(
                            id=("key",),
                            comment="entry comment",
                            value=PatternMessage(["message"]),
                            properties={"prop": PatternMessage(["prop value"])},
                        )
                    ],
                )
            ],
        )
        json = resource_to_json(res)
        assert json == {
            "#": "res comment",
            "@": [["key", "value"]],
            "*": [
                {
                    "@": [["key", "value 1"], ["key", "value 2"]],
                    "#": "section comment",
                    "~": {
                        "key": {
                            "#": "entry comment",
                            "=": ["message"],
                            "+": {"prop": ["prop value"]},
                        }
                    },
                }
            ],
        }
        validator.validate(json)
        assert resource_from_json(json) == res

    def test_multiple(self):
        res = Resource(
            None,
            [
                Section(("s0",), [Comment("comment")]),
                Section(
                    ("s1",),
                    [
                        Entry(("k1",), PatternMessage(["m1"])),
                        Entry(("k2",), PatternMessage(["m2"])),
                    ],
                ),
                Section(
                    ("s2",),
                    [
                        Entry(("k1",), PatternMessage(["m1"])),
                        Entry(("k2",), PatternMessage(["m2"])),
                    ],
                ),
                Section(
                    ("s3",),
                    [
                        Entry(
                            ("ks",),
                            SelectMessage(
                                declarations={"x": Expression("y")},
                                selectors=(VariableRef("x"),),
                                variants={(CatchallKey(),): ["ms"]},
                            ),
                        ),
                    ],
                ),
            ],
        )
        json = resource_to_json(res)
        assert json == {
            "*": [
                {"id": ["s1"], "~": {"k1": {"=": ["m1"]}, "k2": {"=": ["m2"]}}},
                {"id": ["s2"], "~": {"k1": {"=": ["m1"]}, "k2": {"=": ["m2"]}}},
                {
                    "id": ["s3"],
                    "~": {
                        "ks": {
                            "=": {
                                "alt": [{"keys": [{"*": ""}], "pat": ["ms"]}],
                                "decl": {"x": {"_": "y"}},
                                "sel": ["x"],
                            }
                        }
                    },
                },
            ]
        }
        validator.validate(json)
        res.sections = res.sections[1:]
        assert resource_from_json(json) == res
