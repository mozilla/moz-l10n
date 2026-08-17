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

"""parse.source-error -- the reference resource cannot be parsed."""

from __future__ import annotations

from typing import Any, cast

from moz.l10n.lint.model import SEVERITY, Diagnostic, LintContext, Rule, SourceType

from ._common import parse_fluent, parse_mf2

NAME = "source-error"
RULE = Rule(name=NAME, family="parse", default_severity=SEVERITY.warning)


def parse_check(context: LintContext) -> tuple[SourceType, list[Diagnostic]]:
    if context.raw_source is None:
        return None, []

    if context.is_fluent:
        entity, diagnostic = parse_fluent(context.raw_source, context, RULE, "source")
    else:
        entity, diagnostic = cast(
            Any, parse_mf2(context.raw_source, context, RULE, "source")
        )

    if diagnostic:
        return entity, [diagnostic]

    return entity, []
