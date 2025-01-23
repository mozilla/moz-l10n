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
from unittest import SkipTest, TestCase

from moz.l10n.formats import Format
from moz.l10n.message.data import (
    CatchallKey,
    Expression,
    Markup,
    PatternMessage,
    SelectMessage,
    VariableRef,
)
from moz.l10n.resource.data import Comment, Entry, Metadata, Resource, Section

try:
    from moz.l10n.formats.xliff import xliff_parse, xliff_serialize
except ImportError:
    raise SkipTest("Requires [xml] extra")


hello = files("tests.formats.data").joinpath("hello.xliff").read_bytes()
angular = files("tests.formats.data").joinpath("angular.xliff").read_bytes()
icu_docs = files("tests.formats.data").joinpath("icu-docs.xliff").read_bytes()
xcode = files("tests.formats.data").joinpath("xcode.xliff").read_bytes()


class TestXliff1(TestCase):
    def test_parse_hello(self):
        res = xliff_parse(hello)
        assert res == Resource(
            Format.xliff,
            meta=[
                Metadata("@version", "1.2"),
                Metadata("@xmlns", "urn:oasis:names:tc:xliff:document:1.2"),
            ],
            sections=[
                Section(
                    id=("hello.txt",),
                    meta=[
                        Metadata("@source-language", "en"),
                        Metadata("@target-language", "fr"),
                        Metadata("@datatype", "plaintext"),
                    ],
                    entries=[
                        Entry(
                            id=("hi",),
                            meta=[
                                Metadata("source", "Hello world"),
                                Metadata("alt-trans/target/@xml:lang", "es"),
                                Metadata("alt-trans/target", "Hola mundo"),
                            ],
                            value=PatternMessage(["Bonjour le monde"]),
                        )
                    ],
                )
            ],
        )

    def test_serialize_hello(self):
        res = xliff_parse(hello)
        ser = "".join(xliff_serialize(res))
        assert ser == dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <xliff xmlns="urn:oasis:names:tc:xliff:document:1.2" version="1.2">
              <file original="hello.txt" source-language="en" target-language="fr" datatype="plaintext">
                <body>
                  <trans-unit id="hi">
                    <source>Hello world</source>
                    <target>Bonjour le monde</target>
                    <alt-trans>
                      <target xml:lang="es">Hola mundo</target>
                    </alt-trans>
                  </trans-unit>
                </body>
              </file>
            </xliff>
            """
        )

    def test_parse_angular(self):
        res = xliff_parse(angular)
        assert res == Resource(
            Format.xliff,
            meta=[
                Metadata("@version", "1.2"),
                Metadata("@xmlns", "urn:oasis:names:tc:xliff:document:1.2"),
            ],
            sections=[
                Section(
                    id=("ng2.template",),
                    meta=[
                        Metadata("@source-language", "en"),
                        Metadata("@target-language", "fi"),
                        Metadata("@datatype", "plaintext"),
                    ],
                    entries=[
                        Entry(
                            id=("introductionHeader",),
                            value=PatternMessage(["\n  Hei i18n!\n"]),
                            comment="An introduction header for this sample",
                            meta=[
                                Metadata("@datatype", "html"),
                                Metadata("source", "\n  Hello i18n!\n"),
                                Metadata("context-group/@purpose", "location"),
                                Metadata(
                                    "context-group/context/@context-type",
                                    "sourcefile",
                                ),
                                Metadata(
                                    "context-group/context",
                                    "app/app.component.ts",
                                ),
                                Metadata(
                                    "context-group/context[2]/@context-type",
                                    "linenumber",
                                ),
                                Metadata("context-group/context[2]", "3"),
                                Metadata("note/@priority", "1"),
                                Metadata("note/@from", "description"),
                                Metadata("note[2]/@priority", "1"),
                                Metadata("note[2]/@from", "meaning"),
                                Metadata("note[2]", "User welcome"),
                            ],
                        ),
                        Entry(
                            id=("icu_plural",),
                            value=PatternMessage(
                                [
                                    "{VAR_PLURAL, plural, =0 {juuri nyt} =1 {minuutti sitten} other {",
                                    Markup(
                                        kind="standalone",
                                        name="x",
                                        options={
                                            "id": "INTERPOLATION",
                                            "equiv-text": "{{minutes}}",
                                        },
                                    ),
                                    " minuuttia sitten} }",
                                ],
                            ),
                            meta=[
                                Metadata("@datatype", "html"),
                                Metadata(
                                    "source",
                                    "{VAR_PLURAL, plural, =0 {just now} =1 {one minute ago} other {",
                                ),
                                Metadata("source/x/@id", "INTERPOLATION"),
                                Metadata("source/x/@equiv-text", "{{minutes}}"),
                                Metadata("source", " minutes ago} }"),
                                Metadata("note", ""),
                            ],
                        ),
                    ],
                )
            ],
        )

    def test_serialize_angular(self):
        res = xliff_parse(angular)
        ser = "".join(xliff_serialize(res))
        assert ser == dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <xliff xmlns="urn:oasis:names:tc:xliff:document:1.2" version="1.2">
              <file original="ng2.template" source-language="en" target-language="fi" datatype="plaintext">
                <body>
                  <trans-unit id="introductionHeader" datatype="html">
                    <source>
              Hello i18n!
            </source>
                    <target>
              Hei i18n!
            </target>
                    <context-group purpose="location">
                      <context context-type="sourcefile">app/app.component.ts</context>
                      <context context-type="linenumber">3</context>
                    </context-group>
                    <note priority="1" from="description">An introduction header for this sample</note>
                    <note priority="1" from="meaning">User welcome</note>
                  </trans-unit>
                  <trans-unit id="icu_plural" datatype="html">
                    <source>{VAR_PLURAL, plural, =0 {just now} =1 {one minute ago} other {<x id="INTERPOLATION" equiv-text="{{minutes}}"/> minutes ago} }</source>
                    <target>{VAR_PLURAL, plural, =0 {juuri nyt} =1 {minuutti sitten} other {<x id="INTERPOLATION" equiv-text="{{minutes}}"/> minuuttia sitten} }</target>
                    <note></note>
                  </trans-unit>
                </body>
              </file>
            </xliff>
            """
        )

    def test_parse_icu_docs(self):
        res = xliff_parse(icu_docs)
        assert res == Resource(
            Format.xliff,
            meta=[
                Metadata("@version", "1.2"),
                Metadata(
                    "@xsi:schemaLocation",
                    "urn:oasis:names:tc:xliff:document:1.2 xliff-core-1.2-transitional.xsd",
                ),
                Metadata("@xmlns", "urn:oasis:names:tc:xliff:document:1.2"),
                Metadata("@xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance"),
            ],
            sections=[
                Section(
                    id=("en.txt",),
                    meta=[
                        Metadata("@xml:space", "preserve"),
                        Metadata("@source-language", "en"),
                        Metadata("@datatype", "x-icu-resource-bundle"),
                        Metadata("@date", "2007-06-15T23:20:43Z"),
                        Metadata("header/tool/@tool-id", "genrb-3.3-icu-3.7.1"),
                        Metadata("header/tool/@tool-name", "genrb"),
                    ],
                    entries=[],
                ),
                Section(
                    id=("en.txt", "en"),
                    meta=[Metadata("@restype", "x-icu-table")],
                    entries=[
                        Comment(
                            "The resources for a fictitious Hello World application. The application displays a single window with a logo and the hello message."
                        ),
                        Entry(
                            id=("authors",),
                            value=PatternMessage([]),
                            meta=[
                                Metadata("@resname", "authors"),
                                Metadata("@restype", "x-icu-alias"),
                                Metadata("source", "root/authors"),
                            ],
                        ),
                        Entry(
                            id=("hello",),
                            value=PatternMessage([]),
                            comment="This is the message that the application displays to the user.",
                            meta=[
                                Metadata("@resname", "hello"),
                                Metadata("source", "Hello, world!"),
                            ],
                        ),
                        Entry(
                            id=("logo",),
                            value=PatternMessage(
                                [Expression(None, attributes={"bin-unit": None})]
                            ),
                            meta=[
                                Metadata("@resname", "logo"),
                                Metadata("@mime-type", "image"),
                                Metadata("@restype", "x-icu-binary"),
                                Metadata("@translate", "no"),
                                Metadata(
                                    "comment()",
                                    "The logo to be displayed in the application window.",
                                ),
                                Metadata("bin-source/external-file/@href", "logo.gif"),
                            ],
                        ),
                        Entry(
                            id=("md5_sum",),
                            value=PatternMessage(
                                [Expression(None, attributes={"bin-unit": None})]
                            ),
                            meta=[
                                Metadata("@resname", "md5_sum"),
                                Metadata("@mime-type", "application"),
                                Metadata("@restype", "x-icu-binary"),
                                Metadata("@translate", "no"),
                                Metadata(
                                    "comment()", "The MD5 checksum of the application."
                                ),
                                Metadata(
                                    "bin-source/internal-file/@form", "application"
                                ),
                                Metadata("bin-source/internal-file/@crc", "187654673"),
                                Metadata(
                                    "bin-source/internal-file",
                                    "BCFE765BE0FDFAB22C5F9EFD12C52ABC",
                                ),
                            ],
                        ),
                    ],
                ),
                Section(
                    id=("en.txt", "en", "menus"),
                    meta=[
                        Metadata("@resname", "menus"),
                        Metadata("@restype", "x-icu-table"),
                    ],
                    entries=[
                        Comment("The application menus."),
                    ],
                ),
                Section(
                    id=("en.txt", "en", "menus", "menus_help_menu"),
                    meta=[
                        Metadata("@resname", "help_menu"),
                        Metadata("@restype", "x-icu-table"),
                    ],
                    entries=[
                        Entry(
                            id=("menus_help_menu_name",),
                            value=PatternMessage([]),
                            meta=[
                                Metadata("@resname", "name"),
                                Metadata("source", "Help"),
                            ],
                        )
                    ],
                ),
                Section(
                    id=(
                        "en.txt",
                        "en",
                        "menus",
                        "menus_help_menu",
                        "menus_help_menu_items",
                    ),
                    meta=[
                        Metadata("@resname", "items"),
                        Metadata("@restype", "x-icu-array"),
                    ],
                    entries=[
                        Entry(
                            id=("menus_help_menu_items_0",),
                            value=PatternMessage([]),
                            meta=[Metadata("source", "Help Topics")],
                        ),
                        Entry(
                            id=("menus_help_menu_items_1",),
                            value=PatternMessage([]),
                            meta=[Metadata("source", "About Hello World")],
                        ),
                    ],
                ),
            ],
        )

    def test_serialize_icu_docs(self):
        res = xliff_parse(icu_docs)
        ser = "".join(xliff_serialize(res))
        assert ser == dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <xliff xmlns="urn:oasis:names:tc:xliff:document:1.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.2" xsi:schemaLocation="urn:oasis:names:tc:xliff:document:1.2 xliff-core-1.2-transitional.xsd">
              <file original="en.txt" xml:space="preserve" source-language="en" datatype="x-icu-resource-bundle" date="2007-06-15T23:20:43Z">
                <header>
                  <tool tool-id="genrb-3.3-icu-3.7.1" tool-name="genrb"/>
                </header>
                <body>
                  <group id="en" restype="x-icu-table">
                    <!-- The resources for a fictitious Hello World application. The application displays a single window with a logo and the hello message. -->
                    <trans-unit id="authors" resname="authors" restype="x-icu-alias">
                      <source>root/authors</source>
                      <target/>
                    </trans-unit>
                    <trans-unit id="hello" resname="hello">
                      <source>Hello, world!</source>
                      <target/>
                      <note>This is the message that the application displays to the user.</note>
                    </trans-unit>
                    <bin-unit id="logo" resname="logo" mime-type="image" restype="x-icu-binary" translate="no">
                      <!--The logo to be displayed in the application window.-->
                      <bin-source>
                        <external-file href="logo.gif"/>
                      </bin-source>
                    </bin-unit>
                    <bin-unit id="md5_sum" resname="md5_sum" mime-type="application" restype="x-icu-binary" translate="no">
                      <!--The MD5 checksum of the application.-->
                      <bin-source>
                        <internal-file form="application" crc="187654673">BCFE765BE0FDFAB22C5F9EFD12C52ABC</internal-file>
                      </bin-source>
                    </bin-unit>
                    <group id="menus" resname="menus" restype="x-icu-table">
                      <!-- The application menus. -->
                      <group id="menus_help_menu" resname="help_menu" restype="x-icu-table">
                        <trans-unit id="menus_help_menu_name" resname="name">
                          <source>Help</source>
                          <target/>
                        </trans-unit>
                        <group id="menus_help_menu_items" resname="items" restype="x-icu-array">
                          <trans-unit id="menus_help_menu_items_0">
                            <source>Help Topics</source>
                            <target/>
                          </trans-unit>
                          <trans-unit id="menus_help_menu_items_1">
                            <source>About Hello World</source>
                            <target/>
                          </trans-unit>
                        </group>
                      </group>
                    </group>
                  </group>
                </body>
              </file>
            </xliff>
            """
        )

    def test_trim_comments(self):
        res = xliff_parse(icu_docs)
        ser = "".join(xliff_serialize(res, trim_comments=True))
        assert ser == dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <xliff xmlns="urn:oasis:names:tc:xliff:document:1.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.2" xsi:schemaLocation="urn:oasis:names:tc:xliff:document:1.2 xliff-core-1.2-transitional.xsd">
              <file original="en.txt" xml:space="preserve" source-language="en" datatype="x-icu-resource-bundle" date="2007-06-15T23:20:43Z">
                <header>
                  <tool tool-id="genrb-3.3-icu-3.7.1" tool-name="genrb"/>
                </header>
                <body>
                  <group id="en" restype="x-icu-table">
                    <trans-unit id="authors" resname="authors" restype="x-icu-alias">
                      <source>root/authors</source>
                      <target/>
                    </trans-unit>
                    <trans-unit id="hello" resname="hello">
                      <source>Hello, world!</source>
                      <target/>
                    </trans-unit>
                    <bin-unit id="logo" resname="logo" mime-type="image" restype="x-icu-binary" translate="no">
                      <!--The logo to be displayed in the application window.-->
                      <bin-source>
                        <external-file href="logo.gif"/>
                      </bin-source>
                    </bin-unit>
                    <bin-unit id="md5_sum" resname="md5_sum" mime-type="application" restype="x-icu-binary" translate="no">
                      <!--The MD5 checksum of the application.-->
                      <bin-source>
                        <internal-file form="application" crc="187654673">BCFE765BE0FDFAB22C5F9EFD12C52ABC</internal-file>
                      </bin-source>
                    </bin-unit>
                    <group id="menus" resname="menus" restype="x-icu-table">
                      <group id="menus_help_menu" resname="help_menu" restype="x-icu-table">
                        <trans-unit id="menus_help_menu_name" resname="name">
                          <source>Help</source>
                          <target/>
                        </trans-unit>
                        <group id="menus_help_menu_items" resname="items" restype="x-icu-array">
                          <trans-unit id="menus_help_menu_items_0">
                            <source>Help Topics</source>
                            <target/>
                          </trans-unit>
                          <trans-unit id="menus_help_menu_items_1">
                            <source>About Hello World</source>
                            <target/>
                          </trans-unit>
                        </group>
                      </group>
                    </group>
                  </group>
                </body>
              </file>
            </xliff>
            """
        )

    def test_parse_xcode(self):
        res = xliff_parse(xcode)
        assert res == Resource(
            Format.xliff,
            meta=[
                Metadata("@version", "1.2"),
                Metadata(
                    "@xsi:schemaLocation",
                    "urn:oasis:names:tc:xliff:document:1.2 http://docs.oasis-open.org/xliff/v1.2/os/xliff-core-1.2-strict.xsd",
                ),
                Metadata("@xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance"),
                Metadata("@xmlns", "urn:oasis:names:tc:xliff:document:1.2"),
            ],
            sections=[
                Section(
                    id=("xcode1/en.lproj/Localizable.strings",),
                    meta=[
                        Metadata("@source-language", "en"),
                        Metadata("@target-language", "it"),
                        Metadata("@datatype", "plaintext"),
                        Metadata("header/tool/@tool-id", "com.apple.dt.xcode"),
                        Metadata("header/tool/@tool-name", "Xcode"),
                        Metadata("header/tool/@tool-version", "15.2"),
                        Metadata("header/tool/@build-num", "15C500b"),
                    ],
                    entries=[
                        Entry(
                            id=(
                                "[KeyFile/Delete/Confirm/text] Delete key file?\n Make sure you have a backup.",
                            ),
                            value=PatternMessage(
                                [
                                    "Eliminare il file chiave?\nAssicurati di avere una copia."
                                ]
                            ),
                            comment="Message to confirm deletion of a key file.",
                            meta=[
                                Metadata("@xml:space", "preserve"),
                                Metadata(
                                    "source",
                                    "Delete key file?\n Make sure you have a backup.",
                                ),
                                Metadata("target/@state", "translated"),
                            ],
                        )
                    ],
                ),
                Section(
                    id=("xcode1/en.lproj/Localizable.stringsdict",),
                    meta=[
                        Metadata("@source-language", "en"),
                        Metadata("@target-language", "it"),
                        Metadata("@datatype", "plaintext"),
                        Metadata("header/tool/@tool-id", "com.apple.dt.xcode"),
                        Metadata("header/tool/@tool-name", "Xcode"),
                        Metadata("header/tool/@tool-version", "15.2"),
                        Metadata("header/tool/@build-num", "15C500b"),
                    ],
                    entries=[
                        Entry(
                            id=("[Generic/Count/EntriesSelected]",),
                            value=SelectMessage(
                                declarations={
                                    "GenericCountEntriesSelected": Expression(
                                        VariableRef("GenericCountEntriesSelected"),
                                        "number",
                                        attributes={"source": None},
                                    )
                                },
                                selectors=(VariableRef("GenericCountEntriesSelected"),),
                                variants={
                                    ("one",): [
                                        Expression(
                                            VariableRef("int"),
                                            "integer",
                                            attributes={"source": "%d"},
                                        ),
                                        " voce selezionata",
                                    ],
                                    (CatchallKey("other"),): [
                                        Expression(
                                            VariableRef("int"),
                                            "integer",
                                            attributes={"source": "%d"},
                                        ),
                                        " voci selezionate",
                                    ],
                                },
                            ),
                            meta=[
                                Metadata("one/source", "%d entry selected"),
                                Metadata("one/target/@state", "translated"),
                                Metadata("other/source", "%d entries selected"),
                                Metadata("other/target/@state", "translated"),
                            ],
                        ),
                        Entry(
                            id=("[Generic/Count/Threads]",),
                            value=SelectMessage(
                                declarations={
                                    "GenericCountThreads": Expression(
                                        VariableRef("GenericCountThreads"),
                                        "number",
                                        attributes={"source": None},
                                    )
                                },
                                selectors=(VariableRef("GenericCountThreads"),),
                                variants={
                                    ("one",): [
                                        Expression(
                                            VariableRef("int"),
                                            "integer",
                                            attributes={"source": "%d"},
                                        ),
                                        " thread",
                                    ],
                                    (CatchallKey(value="other"),): [
                                        Expression(
                                            VariableRef("int"),
                                            "integer",
                                            attributes={"source": "%d"},
                                        ),
                                        " thread",
                                    ],
                                },
                            ),
                            meta=[
                                Metadata("one/source", "%d thread"),
                                Metadata("one/target/@state", "translated"),
                                Metadata("other/source", "%d threads"),
                                Metadata("other/target/@state", "translated"),
                            ],
                        ),
                    ],
                ),
                Section(
                    id=("xcode2/en.lproj/Localizable.stringsdict",),
                    meta=[
                        Metadata("@source-language", "en"),
                        Metadata("@target-language", "en"),
                        Metadata("@datatype", "plaintext"),
                    ],
                    entries=[
                        Entry(
                            id=("followed_by_three_and_others",),
                            meta=[
                                Metadata("one/@xml:space", "preserve"),
                                Metadata(
                                    "one/source",
                                    "Followed by %2$@, %3$@, %4$@ & %1$d other",
                                ),
                                Metadata("other/@xml:space", "preserve"),
                                Metadata(
                                    "other/source",
                                    "Followed by %2$@, %3$@, %4$@ & %1$d others",
                                ),
                            ],
                            value=SelectMessage(
                                declarations={
                                    "OTHERS": Expression(
                                        VariableRef("OTHERS"),
                                        "number",
                                        attributes={"source": "%#@OTHERS@"},
                                    )
                                },
                                selectors=(VariableRef("OTHERS"),),
                                variants={
                                    ("one",): [
                                        "Followed by ",
                                        Expression(
                                            VariableRef("arg2"),
                                            attributes={"source": "%2$@"},
                                        ),
                                        ", ",
                                        Expression(
                                            VariableRef("arg3"),
                                            attributes={"source": "%3$@"},
                                        ),
                                        ", ",
                                        Expression(
                                            VariableRef("arg4"),
                                            attributes={"source": "%4$@"},
                                        ),
                                        " & ",
                                        Expression(
                                            VariableRef("int1"),
                                            "integer",
                                            attributes={"source": "%1$d"},
                                        ),
                                        " other",
                                    ],
                                    (CatchallKey("other"),): [
                                        "Followed by ",
                                        Expression(
                                            VariableRef("arg2"),
                                            attributes={"source": "%2$@"},
                                        ),
                                        ", ",
                                        Expression(
                                            VariableRef("arg3"),
                                            attributes={"source": "%3$@"},
                                        ),
                                        ", ",
                                        Expression(
                                            VariableRef("arg4"),
                                            attributes={"source": "%4$@"},
                                        ),
                                        " & ",
                                        Expression(
                                            VariableRef("int1"),
                                            "integer",
                                            attributes={"source": "%1$d"},
                                        ),
                                        " others",
                                    ],
                                },
                            ),
                        ),
                    ],
                ),
            ],
        )

    def test_serialize_xcode(self):
        res = xliff_parse(xcode)
        ser = "".join(xliff_serialize(res))
        assert ser == dedent(
            """\
            <?xml version="1.0" encoding="utf-8"?>
            <xliff xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="urn:oasis:names:tc:xliff:document:1.2" version="1.2" xsi:schemaLocation="urn:oasis:names:tc:xliff:document:1.2 http://docs.oasis-open.org/xliff/v1.2/os/xliff-core-1.2-strict.xsd">
              <file original="xcode1/en.lproj/Localizable.strings" source-language="en" target-language="it" datatype="plaintext">
                <header>
                  <tool tool-id="com.apple.dt.xcode" tool-name="Xcode" tool-version="15.2" build-num="15C500b"/>
                </header>
                <body>
                  <trans-unit id="[KeyFile/Delete/Confirm/text] Delete key file?&#10; Make sure you have a backup." xml:space="preserve">
                    <source>Delete key file?
             Make sure you have a backup.</source>
                    <target state="translated">Eliminare il file chiave?
            Assicurati di avere una copia.</target>
                    <note>Message to confirm deletion of a key file.</note>
                  </trans-unit>
                </body>
              </file>
              <file original="xcode1/en.lproj/Localizable.stringsdict" source-language="en" target-language="it" datatype="plaintext">
                <header>
                  <tool tool-id="com.apple.dt.xcode" tool-name="Xcode" tool-version="15.2" build-num="15C500b"/>
                </header>
                <body>
                  <trans-unit id="/[Generic/Count/EntriesSelected]:dict/GenericCountEntriesSelected:dict/one:dict/:string">
                    <source>%d entry selected</source>
                    <target state="translated">%d voce selezionata</target>
                  </trans-unit>
                  <trans-unit id="/[Generic/Count/EntriesSelected]:dict/GenericCountEntriesSelected:dict/other:dict/:string">
                    <source>%d entries selected</source>
                    <target state="translated">%d voci selezionate</target>
                  </trans-unit>
                  <trans-unit id="/[Generic/Count/Threads]:dict/GenericCountThreads:dict/one:dict/:string">
                    <source>%d thread</source>
                    <target state="translated">%d thread</target>
                  </trans-unit>
                  <trans-unit id="/[Generic/Count/Threads]:dict/GenericCountThreads:dict/other:dict/:string">
                    <source>%d threads</source>
                    <target state="translated">%d thread</target>
                  </trans-unit>
                </body>
              </file>
              <file original="xcode2/en.lproj/Localizable.stringsdict" source-language="en" target-language="en" datatype="plaintext">
                <body>
                  <trans-unit id="/followed_by_three_and_others:dict/NSStringLocalizedFormatKey:dict/:string">
                    <source>%#@OTHERS@</source>
                    <target>%#@OTHERS@</target>
                  </trans-unit>
                  <trans-unit id="/followed_by_three_and_others:dict/OTHERS:dict/one:dict/:string" xml:space="preserve">
                    <source>Followed by %2$@, %3$@, %4$@ &amp; %1$d other</source>
                    <target>Followed by %2$@, %3$@, %4$@ &amp; %1$d other</target>
                  </trans-unit>
                  <trans-unit id="/followed_by_three_and_others:dict/OTHERS:dict/other:dict/:string" xml:space="preserve">
                    <source>Followed by %2$@, %3$@, %4$@ &amp; %1$d others</source>
                    <target>Followed by %2$@, %3$@, %4$@ &amp; %1$d others</target>
                  </trans-unit>
                </body>
              </file>
            </xliff>
            """
        )
