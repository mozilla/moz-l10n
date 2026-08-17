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

"""parse.translation-error - The translation cannot be parsed in its target format."""

from __future__ import annotations

from typing import Any, cast

from moz.l10n.lint.model import SEVERITY, Diagnostic, LintContext, Rule, TargetType

from ._common import parse_fluent, parse_mf2

NAME = "translation-error"
RULE = Rule(name=NAME, family="parse", default_severity=SEVERITY.error)


def parse_check(context: LintContext) -> tuple[TargetType, list[Diagnostic]]:
    """Try parsing the raw translation according to context.
    Returned parsed resource if succeeded. Otherwise:
    Translation parse failure is terminal! Pass `None` downstream.
    """
    # Emptiness is content.empty-translation's call, not a parse error.
    if context.raw_translation is None:
        return None, []

    if context.is_fluent:
        target, diagnostic = parse_fluent(
            context.raw_translation, context, RULE, "translation"
        )
    else:
        target, diagnostic = cast(
            Any, parse_mf2(context.raw_translation, context, RULE, "translation")
        )
    if diagnostic:
        # Translation parse failure is terminal! Pass nothing downstream!
        return None, [diagnostic]

    return target, []
