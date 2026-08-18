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

"""
Lint helper functionality.
Basically "borrowed" from the pontoon custom checks for now.
"""

from __future__ import annotations

from collections.abc import Iterable
from json import dumps

from moz.l10n.formats.mf2 import mf2_serialize_message
from moz.l10n.model import (
    CatchallKey,
    Expression,
    Markup,
    Message,
    Pattern,
    PatternMessage,
    SelectMessage,
    VariableRef,
)


def get_patterns(msg: Message) -> Iterable[Pattern]:
    """Every pattern of `msg`; one for a `PatternMessage`, all variants otherwise."""
    return (msg.pattern,) if isinstance(msg, PatternMessage) else msg.variants.values()


def as_simple_pattern(msg: Message | Pattern) -> Pattern:
    """The single pattern of `msg`, selecting the fallback variant if it has several."""
    if isinstance(msg, PatternMessage):
        return msg.pattern
    if isinstance(msg, SelectMessage):
        return next(
            pattern
            for keys, pattern in msg.variants.items()
            if all(isinstance(key, CatchallKey) for key in keys)
        )
    return msg


def get_simple_preview(msg: Message | Pattern) -> str:
    """Flatten an AST message or pattern into its format-native text representation."""
    pattern = as_simple_pattern(msg)
    return "".join(preview_placeholder(part) for part in pattern)


def preview_placeholder(part: str | Expression | Markup) -> str:
    """Render a single pattern element as it was spelled in the original format."""
    if isinstance(part, str):
        return part
    if isinstance(ps := part.attributes.get("source", None), str):
        return ps
    if isinstance(part, Expression):
        if part.function == "html" and isinstance(part.arg, str):
            return part.arg
        elif part.function == "entity" and isinstance(part.arg, VariableRef):
            return part.arg.name
    elif part.kind in ("open", "standalone"):
        res = "<" + part.name
        for name, val in part.options.items():
            value_str = dumps(val) if isinstance(val, str) else "$" + val.name
            res += f" {name}={value_str}"
        res += ">" if part.kind == "open" else " />"
        return res
    elif part.kind == "close" and not part.options:
        return f"</{part.name}>"

    # Fallback for unhandled expressions
    return mf2_serialize_message(PatternMessage([part]))
