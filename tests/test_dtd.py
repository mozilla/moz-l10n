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

from moz.l10n.dtd import dtd_parse, dtd_serialize
from moz.l10n.resource import Comment, Entry, Resource, Section

# Show full diff in self.assertEqual. https://stackoverflow.com/a/61345284
# __import__("sys").modules["unittest.util"]._MAX_LENGTH = 999999999


class TestDtd(TestCase):
    def testFile(self):
        bytes = files("tests.data").joinpath("accounts.dtd").read_bytes()
        res = dtd_parse(bytes.decode())
        self.assertEqual(
            res,
            Resource(
                [
                    Section(
                        [],
                        [
                            Comment(
                                "This file is originally from:\n"
                                "https://searchfox.org/comm-central/rev/1032c05ab3f8f1a7b9b928cc5a79dbf67a9ac48f/chat/locales/en-US/accounts.dtd"
                            ),
                            Entry(
                                ["accounts.title"],
                                "Accounts - &brandShortName;",
                                comment="Account manager window for Instantbird",
                            ),
                            Entry(
                                ["accountsWindow.title"],
                                "Instant messaging status",
                                comment="Instant messaging account status window for Thunderbird",
                            ),
                            Entry(["accountManager.newAccount.label"], "New Account"),
                            Entry(["accountManager.newAccount.accesskey"], "N"),
                            Entry(["accountManager.close.label"], "Close"),
                            Entry(["accountManager.close.accesskey"], "l"),
                            Entry(
                                ["accountManager.close.commandkey"],
                                "a",
                                comment="This should match account.commandkey in instantbird.dtd",
                            ),
                            Entry(
                                ["accountManager.noAccount.title"],
                                "No account configured yet",
                                comment="This title must be short, displayed with a big font size",
                            ),
                            Entry(
                                ["accountManager.noAccount.description"],
                                "Click on the &accountManager.newAccount.label; button to let &brandShortName; guide you through the process of configuring one.",
                            ),
                            Entry(["account.autoSignOn.label"], "Sign-on at startup"),
                            Entry(["account.autoSignOn.accesskey"], "S"),
                            Entry(["account.connect.label"], "Connect"),
                            Entry(["account.connect.accesskey"], "o"),
                            Entry(["account.disconnect.label"], "Disconnect"),
                            Entry(["account.disconnect.accesskey"], "i"),
                            Entry(["account.edit.label"], "Properties"),
                            Entry(["account.edit.accesskey"], "P"),
                            Entry(
                                ["account.cancelReconnection.label"],
                                "Cancel reconnection",
                            ),
                            Entry(["account.cancelReconnection.accesskey"], "A"),
                            Entry(["account.copyDebugLog.label"], "Copy Debug Log"),
                            Entry(["account.copyDebugLog.accesskey"], "C"),
                            Entry(["account.connecting"], "Connecting…"),
                            Entry(["account.disconnecting"], "Disconnecting…"),
                            Entry(["account.disconnected"], "Not Connected"),
                        ],
                    )
                ],
                comment="This Source Code Form is subject to the terms of the Mozilla Public\n"
                "   - License, v. 2.0. If a copy of the MPL was not distributed with this\n"
                "   - file, You can obtain one at http://mozilla.org/MPL/2.0/.",
            ),
        )
        res.sections[0].entries.insert(0, Entry(["foo"], '"bar"'))
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

        self.assertEqual(
            "".join(dtd_serialize(res, trim_comments=True)),
            dedent(
                """\
                <!ENTITY foo '"bar"'>
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

        res.sections[0].entries.insert(0, Entry(["fail me"], "bar"))
        with self.assertRaises(ValueError):
            "".join(dtd_serialize(res))
