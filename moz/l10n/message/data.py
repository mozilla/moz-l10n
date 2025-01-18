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
    "Declaration",
    "Expression",
    "FunctionAnnotation",
    "Markup",
    "Message",
    "Pattern",
    "PatternMessage",
    "SelectMessage",
    "VariableRef",
    "Variants",
]


@dataclass
class VariableRef:
    name: str


@dataclass
class FunctionAnnotation:
    name: str
    options: dict[str, str | VariableRef] = field(default_factory=dict)


@dataclass
class Expression:
    """
    A valid Expression must contain a non-None `arg`, `annotation`, or both.
    """

    arg: str | VariableRef | None
    function: FunctionAnnotation | None = None
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
class Declaration:
    name: str
    value: Expression


@dataclass
class PatternMessage:
    """
    A message without selectors and with a single pattern.
    """

    pattern: Pattern
    declarations: list[Declaration] = field(default_factory=list)

    def placeholders(self) -> set[Expression | Markup]:
        return {part for part in self.pattern if not isinstance(part, str)}


Variants = Dict[Tuple[Union[str, CatchallKey], ...], Pattern]


@dataclass
class SelectMessage:
    """
    A message with one or more selectors and a corresponding number of variants.
    """

    selectors: list[VariableRef]
    variants: Variants
    declarations: list[Declaration] = field(default_factory=list)

    def placeholders(self) -> set[Expression | Markup]:
        return {
            part
            for pattern in self.variants.values()
            for part in pattern
            if not isinstance(part, str)
        }

    def selector_expressions(self) -> list[Expression]:
        return [
            next(decl.value for decl in self.declarations if decl.name == var.name)
            for var in self.selectors
        ]


Message = Union[PatternMessage, SelectMessage]
