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

"""invalid-localizable-entry -- a Fluent translation must be a Message or Term."""

from __future__ import annotations

from fluent.syntax import FluentParser
from fluent.syntax import ast as ftl
from moz.l10n.lint.model import Diagnostic, LintContext, Rule, SourceType, TargetType

NAME = "invalid-localizable-entry"
RULE = Rule(name=NAME, family="structure", default_severity="error")

MESSAGE = "Translation needs to be a valid localizable entry"


def check(
    translation: TargetType, source: SourceType, context: LintContext
) -> list[Diagnostic]:
    """
    Report a Fluent translation that parses into something other than a
    localizable entry -- a standalone comment, say.

    `FluentParser.parse_entry()` reports anything that isn't a Message or Term
    as `Junk`, so a bare comment is indistinguishable from a syntax error at
    that level. Re-parsing as a whole resource tells the two apart: content
    that yields exactly one non-Junk entry is well-formed Fluent that simply
    isn't localizable, while anything else is a genuine `parse-error`.
    """
    if context.resource_format != "fluent":
        return []

    if isinstance(translation, ftl.Junk) and context.raw_translation is not None:
        body = FluentParser(with_spans=False).parse(context.raw_translation).body
        if len(body) != 1 or isinstance(body[0], ftl.Junk):
            return []
    elif isinstance(translation, (ftl.Message, ftl.Term)):
        return []
    return [
        RULE.diagnostic(MESSAGE, severity=context.severity_of(RULE), key=context.key)
    ]
