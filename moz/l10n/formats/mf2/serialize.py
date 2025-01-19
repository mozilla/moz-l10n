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

from collections.abc import Iterator
from re import compile

from ...message import data as msg
from .message_parser import name_re, number_re

complex_start_re = compile(r"[\t\n\r \u3000]*\.")
identifier_re = compile(f"{name_re.pattern}(?::{name_re.pattern})?")
literal_esc_re = compile(r"[\\|]")
text_esc_re = compile(r"[\\{}]")


class MF2SerializeError(ValueError):
    pass


def mf2_serialize_message(message: msg.Message) -> Iterator[str]:
    """
    Serialize a message using MessageFormat 2 syntax.
    """
    if (
        isinstance(message, msg.PatternMessage)
        and not message.declarations
        and (
            not message.pattern
            or not isinstance(part0 := message.pattern[0], str)
            or not complex_start_re.match(part0)
        )
    ):
        # simple message
        yield from mf2_serialize_pattern(message.pattern)
        return

    for name, expr in message.declarations.items():
        # TODO: Fix order by dependencies
        if isinstance(expr.arg, msg.VariableRef) and expr.arg.name == name:
            yield ".input "
        else:
            yield f".local {_variable(name)} = "
        yield from _expression(expr)
        yield "\n"

    if isinstance(message, msg.PatternMessage):
        yield from _quoted_pattern(message.pattern)
    else:
        assert isinstance(message, msg.SelectMessage)
        yield ".match"
        for sel in message.selectors:
            yield f" {_variable(sel.name)}"
        for keys, pattern in message.variants.items():
            yield "\n"
            for key in keys:
                yield "* " if isinstance(key, msg.CatchallKey) else f"{_literal(key)} "
            yield from _quoted_pattern(pattern)


def mf2_serialize_pattern(pattern: msg.Pattern) -> Iterator[str]:
    if not pattern:
        yield ""
    for part in pattern:
        if isinstance(part, msg.Expression):
            yield from _expression(part)
        elif isinstance(part, msg.Markup):
            yield from _markup(part)
        else:
            assert isinstance(part, str)
            yield text_esc_re.sub(r"\\\g<0>", part)


def _quoted_pattern(pattern: msg.Pattern) -> Iterator[str]:
    yield "{{"
    yield from mf2_serialize_pattern(pattern)
    yield "}}"


def _expression(expr: msg.Expression) -> Iterator[str]:
    yield "{"
    if expr.arg:
        yield _value(expr.arg)
    if expr.function:
        if not identifier_re.fullmatch(expr.function):
            raise MF2SerializeError(f"Invalid function name: {expr.function}")
        yield f" :{expr.function}" if expr.arg else f":{expr.function}"
    elif not expr.arg:
        raise MF2SerializeError("Invalid expression with no operand and no function")
    elif expr.options:
        raise MF2SerializeError("Invalid expression with options but no function")
    yield from _options(expr.options)
    yield from _attributes(expr.attributes)
    yield "}"


def _markup(markup: msg.Markup) -> Iterator[str]:
    yield "{/" if markup.kind == "close" else "{#"
    if not identifier_re.fullmatch(markup.name):
        raise MF2SerializeError(f"Invalid markup name: {markup.name}")
    yield markup.name
    yield from _options(markup.options)
    yield from _attributes(markup.attributes)
    yield "/}" if markup.kind == "standalone" else "}"


def _options(options: dict[str, str | msg.VariableRef]) -> Iterator[str]:
    for name, value in options.items():
        if not identifier_re.fullmatch(name):
            raise MF2SerializeError(f"Invalid option name: {name}")
        yield f" {name}={_value(value)}"


def _attributes(attributes: dict[str, str | None]) -> Iterator[str]:
    for name, value in attributes.items():
        if not identifier_re.fullmatch(name):
            raise MF2SerializeError(f"Invalid attribute name: {name}")
        if value is None:
            yield f" @{name}"
        else:
            yield f" @{name}={_literal(value)}"


def _value(value: str | msg.VariableRef) -> str:
    if isinstance(value, str):
        return _literal(value)
    else:
        assert isinstance(value, msg.VariableRef)
        return _variable(value.name)


def _variable(name: str) -> str:
    if not name_re.fullmatch(name):
        raise MF2SerializeError(f"Invalid variable name: {name}")
    return f"${name}"


def _literal(literal: str) -> str:
    if name_re.fullmatch(literal) or number_re.fullmatch(literal):
        return literal
    esc_literal = literal_esc_re.sub(r"\\\g<0>", literal)
    return f"|{esc_literal}|"
