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

# ruff: noqa: RUF001

from __future__ import annotations

from importlib_resources import files
from unittest import TestCase

from moz.l10n.formats import Format
from moz.l10n.formats.gettext import gettext_parse, gettext_serialize
from moz.l10n.model import (
    CatchallKey,
    Entry,
    Expression,
    Metadata,
    PatternMessage,
    Resource,
    Section,
    SelectMessage,
    VariableRef,
)

res_path = str(files("tests.formats.data").joinpath("foo.po"))


class TestGettext(TestCase):
    def test_parse(self):
        res = gettext_parse(res_path)
        assert res == Resource(
            Format.gettext,
            comment="Test translation file.\n"
            "Any copyright is dedicated to the Public Domain.\n"
            "http://creativecommons.org/publicdomain/zero/1.0/",
            meta=[
                Metadata("Project-Id-Version", "foo"),
                Metadata("POT-Creation-Date", "2008-02-06 16:25-0500"),
                Metadata("PO-Revision-Date", "2008-02-09 15:23+0200"),
                Metadata("Last-Translator", "Foo Bar <foobar@example.org>"),
                Metadata("Language-Team", "Fake <fake@example.org>"),
                Metadata("MIME-Version", "1.0"),
                Metadata("Content-Type", "text/plain; charset=UTF-8"),
                Metadata("Content-Transfer-Encoding", "8bit"),
                Metadata("Language", "sl"),
                Metadata(
                    "Plural-Forms",
                    "nplurals=4; plural=(n%100==1 ? 1 : n%100==2 ? 2 : n%100==3 || n%100==4 ? 3 : 0);",
                ),
            ],
            sections=[
                Section(
                    id=(),
                    entries=[
                        Entry(
                            ("original string",),
                            PatternMessage(["translated string"]),
                        ),
                        Entry(
                            ("%d translated message",),
                            meta=[
                                Metadata("reference", "src/msgfmt.c:876"),
                                Metadata("flag", "c-format"),
                                Metadata("plural", "%d translated messages"),
                            ],
                            value=SelectMessage(
                                declarations={
                                    "n": Expression(VariableRef("n"), "number")
                                },
                                selectors=(VariableRef("n"),),
                                variants={
                                    ("0",): ["%d prevedenih sporočil"],
                                    ("1",): ["%d prevedeno sporočilo"],
                                    ("2",): ["%d prevedeni sporočili"],
                                    (CatchallKey("3"),): ["%d prevedena sporočila"],
                                },
                            ),
                        ),
                        Entry(
                            ("original string", "context"),
                            PatternMessage(["translated string"]),
                        ),
                        Entry(
                            ("obsolete string",),
                            meta=[Metadata("obsolete", "true")],
                            value=PatternMessage(["translated string"]),
                        ),
                        Entry(("other string",), PatternMessage(["translated string"])),
                        Entry(("line\u2028separator",), PatternMessage([""])),
                    ],
                ),
            ],
        )

    def test_serialize(self):
        res = gettext_parse(res_path)
        exp = r"""# Test translation file.
# Any copyright is dedicated to the Public Domain.
# http://creativecommons.org/publicdomain/zero/1.0/
#
msgid ""
msgstr ""
"Project-Id-Version: foo\n"
"POT-Creation-Date: 2008-02-06 16:25-0500\n"
"PO-Revision-Date: 2008-02-09 15:23+0200\n"
"Last-Translator: Foo Bar <foobar@example.org>\n"
"Language-Team: Fake <fake@example.org>\n"
"Language: sl\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=4; plural=(n%100==1 ? 1 : n%100==2 ? 2 : n%100==3 || n%100==4 ? 3 : 0);\n"

msgid "original string"
msgstr "translated string"

#: src/msgfmt.c:876
#, c-format
msgid "%d translated message"
msgid_plural "%d translated messages"
msgstr[0] "%d prevedenih sporočil"
msgstr[1] "%d prevedeno sporočilo"
msgstr[2] "%d prevedeni sporočili"
msgstr[3] "%d prevedena sporočila"

msgctxt "context"
msgid "original string"
msgstr "translated string"

#~ msgid "obsolete string"
#~ msgstr "translated string"

msgid "other string"
msgstr "translated string"

msgid ""
"line "
"separator"
msgstr ""
"""
        assert "".join(gettext_serialize(res)) == exp

        # Remove catchall key label
        res.sections[0].entries[1].value.variants = {
            ("0",): ["%d prevedenih sporočil"],
            ("1",): ["%d prevedeno sporočilo"],
            ("2",): ["%d prevedeni sporočili"],
            (CatchallKey(),): ["%d prevedena sporočila"],
        }
        assert "".join(gettext_serialize(res)) == exp

    def test_trim_comments(self):
        res = gettext_parse(res_path)
        assert (
            "".join(gettext_serialize(res, trim_comments=True))
            == r"""#
msgid ""
msgstr ""
"Project-Id-Version: foo\n"
"POT-Creation-Date: 2008-02-06 16:25-0500\n"
"PO-Revision-Date: 2008-02-09 15:23+0200\n"
"Last-Translator: Foo Bar <foobar@example.org>\n"
"Language-Team: Fake <fake@example.org>\n"
"Language: sl\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=4; plural=(n%100==1 ? 1 : n%100==2 ? 2 : n%100==3 || n%100==4 ? 3 : 0);\n"

msgid "original string"
msgstr "translated string"

msgid "%d translated message"
msgid_plural "%d translated messages"
msgstr[0] "%d prevedenih sporočil"
msgstr[1] "%d prevedeno sporočilo"
msgstr[2] "%d prevedeni sporočili"
msgstr[3] "%d prevedena sporočila"

msgctxt "context"
msgid "original string"
msgstr "translated string"

msgid "other string"
msgstr "translated string"

msgid ""
"line "
"separator"
msgstr ""
"""
        )

    def test_obsolete(self):
        res = gettext_parse(res_path)
        res.sections[0].entries[0].meta.append(Metadata("obsolete", "true"))
        res.sections[0].entries[3].meta = []
        assert r"""
"Plural-Forms: nplurals=4; plural=(n%100==1 ? 1 : n%100==2 ? 2 : n%100==3 || n%100==4 ? 3 : 0);\n"

#~ msgid "original string"
#~ msgstr "translated string"

#: src/msgfmt.c:876
#, c-format
msgid "%d translated message"
msgid_plural "%d translated messages"
msgstr[0] "%d prevedenih sporočil"
msgstr[1] "%d prevedeno sporočilo"
msgstr[2] "%d prevedeni sporočili"
msgstr[3] "%d prevedena sporočila"

msgctxt "context"
msgid "original string"
msgstr "translated string"

msgid "obsolete string"
msgstr "translated string"

msgid "other string"
msgstr "translated string"
""" in "".join(gettext_serialize(res))

        res = gettext_parse(res_path, skip_obsolete=True)
        assert [entry.id for entry in res.sections[0].entries] == [
            ("original string",),
            ("%d translated message",),
            ("original string", "context"),
            ("other string",),
            ("line\u2028separator",),
        ]

    def test_named_plurals(self):
        src = r"""#
msgid ""
msgstr ""
"Language: pl\n"
"Plural-Forms: nplurals=3; plural=n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2;\n"

msgid "src-one"
msgid_plural "src-other"
msgstr[0] "pl-one"
msgstr[1] "pl-few"
msgstr[2] "pl-many"
"""
        plurals = ["one", "few", "many"]
        res = gettext_parse(src, plurals=plurals)
        assert res.sections == [
            Section(
                id=(),
                entries=[
                    Entry(
                        ("src-one",),
                        meta=[Metadata("plural", "src-other")],
                        value=SelectMessage(
                            declarations={"n": Expression(VariableRef("n"), "number")},
                            selectors=(VariableRef("n"),),
                            variants={
                                ("one",): ["pl-one"],
                                ("few",): ["pl-few"],
                                (CatchallKey("many"),): ["pl-many"],
                            },
                        ),
                    ),
                ],
            ),
        ]
        assert "".join(gettext_serialize(res, plurals=plurals)) == src

        # Remove catchall key label
        res.sections[0].entries[0].value.variants = {
            ("one",): ["pl-one"],
            ("few",): ["pl-few"],
            (CatchallKey(),): ["pl-many"],
        }
        assert "".join(gettext_serialize(res, plurals=plurals)) == src
