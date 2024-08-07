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
from unittest import TestCase

from moz.l10n.message import (
    Expression,
    FunctionAnnotation,
    PatternMessage,
    SelectMessage,
    VariableRef,
)
from moz.l10n.resource.data import Entry, Metadata, Resource, Section
from moz.l10n.resource.format import Format
from moz.l10n.resource.po import po_parse, po_serialize

source = files("tests.resource.data").joinpath("foo.po").read_bytes().decode("utf-8")


class TestPo(TestCase):
    def test_parse(self):
        res = po_parse(source)
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
                                [
                                    Expression(
                                        VariableRef("n"),
                                        FunctionAnnotation("number"),
                                    )
                                ],
                                {
                                    ("0",): ["%d prevedenih sporočil"],
                                    ("1",): ["%d prevedeno sporočilo"],
                                    ("2",): ["%d prevedeni sporočili"],
                                    ("3",): ["%d prevedena sporočila"],
                                },
                            ),
                        ),
                        Entry(
                            ("obsolete string",),
                            meta=[Metadata("obsolete", "true")],
                            value=PatternMessage(["translated string"]),
                        ),
                        Entry(("other string",), PatternMessage(["translated string"])),
                    ],
                ),
                Section(
                    id=("context",),
                    entries=[
                        Entry(
                            ("original string",),
                            PatternMessage(["translated string"]),
                        )
                    ],
                ),
            ],
        )

    def test_serialize(self):
        res = po_parse(source)
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

#~ msgid "obsolete string"
#~ msgstr "translated string"

msgid "other string"
msgstr "translated string"

msgctxt "context"
msgid "original string"
msgstr "translated string"
"""
        )

    def test_trim_comments(self):
        res = po_parse(source)
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

msgid "other string"
msgstr "translated string"

msgctxt "context"
msgid "original string"
msgstr "translated string"
"""
        )

    def test_obsolete(self):
        res = po_parse(source)
        res.sections[0].entries[0].meta.append(Metadata("obsolete", True))
        res.sections[0].entries[2].meta = []
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

msgid "obsolete string"
msgstr "translated string"

msgid "other string"
msgstr "translated string"

msgctxt "context"
msgid "original string"
msgstr "translated string"
"""
        )
