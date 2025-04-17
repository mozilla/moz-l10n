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
from moz.l10n.formats.po import po_parse, po_serialize
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


class TestPo(TestCase):
    def test_parse(self):
        res = po_parse(res_path)
        assert res == Resource(
            Format.po,
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
        res = po_parse(res_path)
        assert (
            "".join(po_serialize(res))
            == r"""# Test translation file.
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
        )

    def test_trim_comments(self):
        res = po_parse(res_path)
        assert (
            "".join(po_serialize(res, trim_comments=True))
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
        res = po_parse(res_path)
        res.sections[0].entries[0].meta.append(Metadata("obsolete", True))
        res.sections[0].entries[3].meta = []
        assert (
            "".join(po_serialize(res))
            == r"""# Test translation file.
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

msgid ""
"line "
"separator"
msgstr ""
"""
        )
