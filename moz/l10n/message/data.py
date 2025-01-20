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

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Tuple, Union

__all__ = [
    "CatchallKey",
    "Expression",
    "Markup",
    "Message",
    "Pattern",
    "PatternMessage",
    "SelectMessage",
    "VariableRef",
]


@dataclass
class VariableRef:
    name: str


@dataclass
class Expression:
    """
    A valid Expression must contain a non-None `arg`, `function`, or both.

    An Expression with no `function` and non-empty `options` is not valid.
    """

    arg: str | VariableRef | None
    function: str | None = None
    options: dict[str, str | VariableRef] = field(default_factory=dict)
    attributes: dict[str, str | None] = field(default_factory=dict)


@dataclass
class Markup:
    kind: Literal["open", "standalone", "close"]
    name: str
    options: dict[str, str | VariableRef] = field(default_factory=dict)
    attributes: dict[str, str | None] = field(default_factory=dict)


Pattern = List[Union[str, Expression, Markup]]
"""
A linear sequence of text and placeholders corresponding to potential output of a message.

String values represent literal text.
String values include all processing of the underlying text values, including escape sequence processing.
"""


@dataclass
class CatchallKey:
    value: str | None = field(default=None, compare=False)
    """
    An optional string identifier for the default/catch-all variant.
    """

    def __hash__(self) -> int:
        """
        Consider all catchall-keys as equivalent to each other
        """
        return 1


@dataclass
class PatternMessage:
    """
    A message without selectors and with a single pattern.
    """

    pattern: Pattern
    declarations: dict[str, Expression] = field(default_factory=dict)

    def placeholders(self) -> set[Expression | Markup]:
        return {part for part in self.pattern if not isinstance(part, str)}


@dataclass
class SelectMessage:
    """
    A message with one or more selectors and a corresponding number of variants.
    """

    declarations: dict[str, Expression]
    selectors: tuple[VariableRef, ...]
    variants: Dict[Tuple[Union[str, CatchallKey], ...], Pattern]

    def placeholders(self) -> set[Expression | Markup]:
        return {
            part
            for pattern in self.variants.values()
            for part in pattern
            if not isinstance(part, str)
        }

    def selector_expressions(self) -> tuple[Expression, ...]:
        return tuple(self.declarations[var.name] for var in self.selectors)


Message = Union[PatternMessage, SelectMessage]
