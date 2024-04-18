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

from moz.l10n.message import Expression, Markup, PatternMessage
from moz.l10n.resource import Comment, Entry, Metadata, Resource, Section
from moz.l10n.xliff import xliff_parse, xliff_serialize

# Show full diff in self.assertEqual. https://stackoverflow.com/a/61345284
# __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

hello = files("tests.data").joinpath("hello.xliff").read_bytes()
angular = files("tests.data").joinpath("angular.xliff").read_bytes()
icu_docs = files("tests.data").joinpath("icu-docs.xliff").read_bytes()


class TestXliff1(TestCase):
    def test_parse_hello(self):
        res = xliff_parse(hello)
        assert res == Resource(
            meta=[
                Metadata(key="version", value="1.2"),
                Metadata(key="xmlns", value="urn:oasis:names:tc:xliff:document:1.2"),
            ],
            sections=[
                Section(
                    id=["hello.txt"],
                    meta=[
                        Metadata(key="source-language", value="en"),
                        Metadata(key="target-language", value="fr"),
                        Metadata(key="datatype", value="plaintext"),
                    ],
                    entries=[
                        Entry(
                            id=["hi"],
                            meta=[
                                Metadata(key="source/.", value="Hello world"),
                                Metadata(
                                    key="2,alt-trans/0,target/xml:lang", value="es"
                                ),
                                Metadata(
                                    key="2,alt-trans/0,target/.", value="Hola mundo"
                                ),
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
        print(ser)
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
            meta=[
                Metadata(key="version", value="1.2"),
                Metadata(key="xmlns", value="urn:oasis:names:tc:xliff:document:1.2"),
            ],
            sections=[
                Section(
                    id=["ng2.template"],
                    meta=[
                        Metadata(key="source-language", value="en"),
                        Metadata(key="target-language", value="fi"),
                        Metadata(key="datatype", value="plaintext"),
                    ],
                    entries=[
                        Entry(
                            id=["introductionHeader"],
                            value=PatternMessage(["\n  Hei i18n!\n"]),
                            comment="An introduction header for this sample",
                            meta=[
                                Metadata(key="datatype", value="html"),
                                Metadata(key="source/.", value="\n  Hello i18n!\n"),
                                Metadata(
                                    key="2,context-group/purpose", value="location"
                                ),
                                Metadata(
                                    key="2,context-group/0,context/context-type",
                                    value="sourcefile",
                                ),
                                Metadata(
                                    key="2,context-group/0,context/.",
                                    value="app/app.component.ts",
                                ),
                                Metadata(
                                    key="2,context-group/1,context/context-type",
                                    value="linenumber",
                                ),
                                Metadata(key="2,context-group/1,context/.", value="3"),
                                Metadata(key="note/priority", value="1"),
                                Metadata(key="note/from", value="description"),
                                Metadata(key="4,note/priority", value="1"),
                                Metadata(key="4,note/from", value="meaning"),
                                Metadata(key="4,note/.", value="User welcome"),
                            ],
                        ),
                        Entry(
                            id=["icu_plural"],
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
                                Metadata(key="datatype", value="html"),
                                Metadata(
                                    key="source/.",
                                    value="{VAR_PLURAL, plural, =0 {just now} =1 {one minute ago} other {",
                                ),
                                Metadata(key="source/0,x/id", value="INTERPOLATION"),
                                Metadata(
                                    key="source/0,x/equiv-text", value="{{minutes}}"
                                ),
                                Metadata(key="source/.", value=" minutes ago} }"),
                                Metadata(key="2,note/.", value=""),
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
            meta=[
                Metadata(key="version", value="1.2"),
                Metadata(
                    key="xsi:schemaLocation",
                    value="urn:oasis:names:tc:xliff:document:1.2 xliff-core-1.2-transitional.xsd",
                ),
                Metadata(key="xmlns", value="urn:oasis:names:tc:xliff:document:1.2"),
                Metadata(
                    key="xmlns:xsi", value="http://www.w3.org/2001/XMLSchema-instance"
                ),
            ],
            sections=[
                Section(
                    id=["en.txt"],
                    meta=[
                        Metadata(key="xml:space", value="preserve"),
                        Metadata(key="source-language", value="en"),
                        Metadata(key="datatype", value="x-icu-resource-bundle"),
                        Metadata(key="date", value="2007-06-15T23:20:43Z"),
                        Metadata(
                            key="header/0,tool/tool-id", value="genrb-3.3-icu-3.7.1"
                        ),
                        Metadata(key="header/0,tool/tool-name", value="genrb"),
                    ],
                    entries=[],
                ),
                Section(
                    id=["en.txt", "en"],
                    meta=[Metadata(key="restype", value="x-icu-table")],
                    entries=[
                        Comment(
                            "The resources for a fictious Hello World application. The application displays a single window with a logo and the hello message."
                        ),
                        Entry(
                            id=["authors"],
                            value=PatternMessage([]),
                            meta=[
                                Metadata(key="resname", value="authors"),
                                Metadata(key="restype", value="x-icu-alias"),
                                Metadata(key="source/.", value="root/authors"),
                            ],
                        ),
                        Entry(
                            id=["hello"],
                            value=PatternMessage([]),
                            comment="This is the message that the application displays to the user.",
                            meta=[
                                Metadata(key="resname", value="hello"),
                                Metadata(key="source/.", value="Hello, world!"),
                            ],
                        ),
                        Entry(
                            id=["logo"],
                            value=PatternMessage(
                                [Expression(None, attributes={"bin-unit": None})]
                            ),
                            meta=[
                                Metadata(key="resname", value="logo"),
                                Metadata(key="mime-type", value="image"),
                                Metadata(key="restype", value="x-icu-binary"),
                                Metadata(key="translate", value="no"),
                                Metadata(
                                    key="!",
                                    value="The logo to be displayed in the application window.",
                                ),
                                Metadata(
                                    key="1,bin-source/0,external-file/href",
                                    value="logo.gif",
                                ),
                            ],
                        ),
                        Entry(
                            id=["md5_sum"],
                            value=PatternMessage(
                                [Expression(None, attributes={"bin-unit": None})]
                            ),
                            meta=[
                                Metadata(key="resname", value="md5_sum"),
                                Metadata(key="mime-type", value="application"),
                                Metadata(key="restype", value="x-icu-binary"),
                                Metadata(key="translate", value="no"),
                                Metadata(
                                    key="!",
                                    value="The MD5 checksum of the application.",
                                ),
                                Metadata(
                                    key="1,bin-source/0,internal-file/form",
                                    value="application",
                                ),
                                Metadata(
                                    key="1,bin-source/0,internal-file/crc",
                                    value="187654673",
                                ),
                                Metadata(
                                    key="1,bin-source/0,internal-file/.",
                                    value="BCFE765BE0FDFAB22C5F9EFD12C52ABC",
                                ),
                            ],
                        ),
                    ],
                ),
                Section(
                    id=["en.txt", "en", "menus"],
                    meta=[
                        Metadata(key="resname", value="menus"),
                        Metadata(key="restype", value="x-icu-table"),
                    ],
                    entries=[
                        Comment("The application menus."),
                    ],
                ),
                Section(
                    id=["en.txt", "en", "menus", "menus_help_menu"],
                    meta=[
                        Metadata(key="resname", value="help_menu"),
                        Metadata(key="restype", value="x-icu-table"),
                    ],
                    entries=[
                        Entry(
                            id=["menus_help_menu_name"],
                            value=PatternMessage([]),
                            meta=[
                                Metadata(key="resname", value="name"),
                                Metadata(key="source/.", value="Help"),
                            ],
                        )
                    ],
                ),
                Section(
                    id=[
                        "en.txt",
                        "en",
                        "menus",
                        "menus_help_menu",
                        "menus_help_menu_items",
                    ],
                    meta=[
                        Metadata(key="resname", value="items"),
                        Metadata(key="restype", value="x-icu-array"),
                    ],
                    entries=[
                        Entry(
                            id=["menus_help_menu_items_0"],
                            value=PatternMessage([]),
                            meta=[Metadata(key="source/.", value="Help Topics")],
                        ),
                        Entry(
                            id=["menus_help_menu_items_1"],
                            value=PatternMessage([]),
                            meta=[Metadata(key="source/.", value="About Hello World")],
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
                    <!-- The resources for a fictious Hello World application. The application displays a single window with a logo and the hello message. -->
                    <trans-unit id="authors" resname="authors" restype="x-icu-alias">
                      <source>root/authors</source>
                    </trans-unit>
                    <trans-unit id="hello" resname="hello">
                      <source>Hello, world!</source>
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
                        </trans-unit>
                        <group id="menus_help_menu_items" resname="items" restype="x-icu-array">
                          <trans-unit id="menus_help_menu_items_0">
                            <source>Help Topics</source>
                          </trans-unit>
                          <trans-unit id="menus_help_menu_items_1">
                            <source>About Hello World</source>
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
