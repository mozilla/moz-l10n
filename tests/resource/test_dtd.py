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

from moz.l10n.message import PatternMessage
from moz.l10n.resource.data import Comment, Entry, Resource, Section
from moz.l10n.resource.dtd import dtd_parse, dtd_serialize
from moz.l10n.resource.format import Format

# Show full diff in self.assertEqual. https://stackoverflow.com/a/61345284
# __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999

source = (
    files("tests.resource.data").joinpath("accounts.dtd").read_bytes().decode("utf-8")
)


class TestDtd(TestCase):
    def test_parse(self):
        res = dtd_parse(source)
        self.assertEqual(
            res,
            Resource(
                Format.dtd,
                [
                    Section(
                        (),
                        [
                            Comment(
                                "This file is originally from:\n"
                                "https://searchfox.org/comm-central/rev/1032c05ab3f8f1a7b9b928cc5a79dbf67a9ac48f/chat/locales/en-US/accounts.dtd"
                            ),
                            Entry(
                                ("accounts.title",),
                                PatternMessage(["Accounts - &brandShortName;"]),
                                comment="Account manager window for Instantbird",
                            ),
                            Entry(
                                ("accountsWindow.title",),
                                PatternMessage(["Instant messaging status"]),
                                comment="Instant messaging account status window for Thunderbird",
                            ),
                            Entry(
                                ("accountManager.newAccount.label",),
                                PatternMessage(["New Account"]),
                            ),
                            Entry(
                                ("accountManager.newAccount.accesskey",),
                                PatternMessage(["N"]),
                            ),
                            Entry(
                                ("accountManager.close.label",),
                                PatternMessage(["Close"]),
                            ),
                            Entry(
                                ("accountManager.close.accesskey",),
                                PatternMessage(["l"]),
                            ),
                            Entry(
                                ("accountManager.close.commandkey",),
                                PatternMessage(["a"]),
                                comment="This should match account.commandkey in instantbird.dtd",
                            ),
                            Entry(
                                ("accountManager.noAccount.title",),
                                PatternMessage(["No account configured yet"]),
                                comment="This title must be short, displayed with a big font size",
                            ),
                            Entry(
                                ("accountManager.noAccount.description",),
                                PatternMessage(
                                    [
                                        "Click on the &accountManager.newAccount.label; button to let &brandShortName; guide you through the process of configuring one."
                                    ]
                                ),
                            ),
                            Entry(
                                ("account.autoSignOn.label",),
                                PatternMessage(["Sign-on at startup"]),
                            ),
                            Entry(
                                ("account.autoSignOn.accesskey",), PatternMessage(["S"])
                            ),
                            Entry(
                                ("account.connect.label",), PatternMessage(["Connect"])
                            ),
                            Entry(
                                ("account.connect.accesskey",), PatternMessage(["o"])
                            ),
                            Entry(
                                ("account.disconnect.label",),
                                PatternMessage(["Disconnect"]),
                            ),
                            Entry(
                                ("account.disconnect.accesskey",), PatternMessage(["i"])
                            ),
                            Entry(
                                ("account.edit.label",), PatternMessage(["Properties"])
                            ),
                            Entry(("account.edit.accesskey",), PatternMessage(["P"])),
                            Entry(
                                ("account.cancelReconnection.label",),
                                PatternMessage(["Cancel reconnection"]),
                            ),
                            Entry(
                                ("account.cancelReconnection.accesskey",),
                                PatternMessage(["A"]),
                            ),
                            Entry(
                                ("account.copyDebugLog.label",),
                                PatternMessage(["Copy Debug Log"]),
                            ),
                            Entry(
                                ("account.copyDebugLog.accesskey",),
                                PatternMessage(["C"]),
                            ),
                            Entry(
                                ("account.connecting",), PatternMessage(["Connecting…"])
                            ),
                            Entry(
                                ("account.disconnecting",),
                                PatternMessage(["Disconnecting…"]),
                            ),
                            Entry(
                                ("account.disconnected",),
                                PatternMessage(["Not Connected"]),
                            ),
                        ],
                    )
                ],
                comment="This Source Code Form is subject to the terms of the Mozilla Public\n"
                "   - License, v. 2.0. If a copy of the MPL was not distributed with this\n"
                "   - file, You can obtain one at http://mozilla.org/MPL/2.0/.",
            ),
        )

    def test_serialize(self):
        res = dtd_parse(source)
        res.sections[0].entries.insert(0, Entry(("foo",), '"bar"'))
        self.assertEqual(
            "".join(dtd_serialize(res)),
            dedent(
                """\
                <!-- This Source Code Form is subject to the terms of the Mozilla Public
                   - License, v. 2.0. If a copy of the MPL was not distributed with this
                   - file, You can obtain one at http://mozilla.org/MPL/2.0/. -->

                <!ENTITY foo '"bar"'>

                <!-- This file is originally from:
                     https://searchfox.org/comm-central/rev/1032c05ab3f8f1a7b9b928cc5a79dbf67a9ac48f/chat/locales/en-US/accounts.dtd -->

                <!-- Account manager window for Instantbird -->
                <!ENTITY accounts.title "Accounts - &brandShortName;">
                <!-- Instant messaging account status window for Thunderbird -->
                <!ENTITY accountsWindow.title "Instant messaging status">
                <!ENTITY accountManager.newAccount.label "New Account">
                <!ENTITY accountManager.newAccount.accesskey "N">
                <!ENTITY accountManager.close.label "Close">
                <!ENTITY accountManager.close.accesskey "l">
                <!-- This should match account.commandkey in instantbird.dtd -->
                <!ENTITY accountManager.close.commandkey "a">
                <!-- This title must be short, displayed with a big font size -->
                <!ENTITY accountManager.noAccount.title "No account configured yet">
                <!ENTITY accountManager.noAccount.description "Click on the &accountManager.newAccount.label; button to let &brandShortName; guide you through the process of configuring one.">
                <!ENTITY account.autoSignOn.label "Sign-on at startup">
                <!ENTITY account.autoSignOn.accesskey "S">
                <!ENTITY account.connect.label "Connect">
                <!ENTITY account.connect.accesskey "o">
                <!ENTITY account.disconnect.label "Disconnect">
                <!ENTITY account.disconnect.accesskey "i">
                <!ENTITY account.edit.label "Properties">
                <!ENTITY account.edit.accesskey "P">
                <!ENTITY account.cancelReconnection.label "Cancel reconnection">
                <!ENTITY account.cancelReconnection.accesskey "A">
                <!ENTITY account.copyDebugLog.label "Copy Debug Log">
                <!ENTITY account.copyDebugLog.accesskey "C">
                <!ENTITY account.connecting "Connecting…">
                <!ENTITY account.disconnecting "Disconnecting…">
                <!ENTITY account.disconnected "Not Connected">
                """
            ),
        )

    def test_trim_comments(self):
        res = dtd_parse(source)
        self.assertEqual(
            "".join(dtd_serialize(res, trim_comments=True)),
            dedent(
                """\
                <!ENTITY accounts.title "Accounts - &brandShortName;">
                <!ENTITY accountsWindow.title "Instant messaging status">
                <!ENTITY accountManager.newAccount.label "New Account">
                <!ENTITY accountManager.newAccount.accesskey "N">
                <!ENTITY accountManager.close.label "Close">
                <!ENTITY accountManager.close.accesskey "l">
                <!ENTITY accountManager.close.commandkey "a">
                <!ENTITY accountManager.noAccount.title "No account configured yet">
                <!ENTITY accountManager.noAccount.description "Click on the &accountManager.newAccount.label; button to let &brandShortName; guide you through the process of configuring one.">
                <!ENTITY account.autoSignOn.label "Sign-on at startup">
                <!ENTITY account.autoSignOn.accesskey "S">
                <!ENTITY account.connect.label "Connect">
                <!ENTITY account.connect.accesskey "o">
                <!ENTITY account.disconnect.label "Disconnect">
                <!ENTITY account.disconnect.accesskey "i">
                <!ENTITY account.edit.label "Properties">
                <!ENTITY account.edit.accesskey "P">
                <!ENTITY account.cancelReconnection.label "Cancel reconnection">
                <!ENTITY account.cancelReconnection.accesskey "A">
                <!ENTITY account.copyDebugLog.label "Copy Debug Log">
                <!ENTITY account.copyDebugLog.accesskey "C">
                <!ENTITY account.connecting "Connecting…">
                <!ENTITY account.disconnecting "Disconnecting…">
                <!ENTITY account.disconnected "Not Connected">
                """
            ),
        )

    def test_invalid_key(self):
        res = dtd_parse(source)
        res.sections[0].entries.insert(0, Entry(("fail me",), "bar"))
        with self.assertRaises(ValueError):
            "".join(dtd_serialize(res))

    def test_no_whitespace(self):
        res = dtd_parse('<!ENTITY key "value">')
        assert res == Resource(
            Format.dtd, [Section((), [Entry(("key",), PatternMessage(["value"]))])]
        )

        res = dtd_parse('<!-- comment --><!ENTITY key "value">')
        assert res == Resource(
            Format.dtd,
            [
                Section(
                    (), [Entry(("key",), PatternMessage(["value"]), comment="comment")]
                )
            ],
        )

        res = dtd_parse('<!ENTITY one "One"><!ENTITY two "Two">')
        assert res == Resource(
            Format.dtd,
            [
                Section(
                    (),
                    [
                        Entry(("one",), PatternMessage(["One"])),
                        Entry(("two",), PatternMessage(["Two"])),
                    ],
                )
            ],
        )
