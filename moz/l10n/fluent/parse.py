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

from collections.abc import Callable, Generator
from itertools import product
from typing import cast, overload

from fluent.syntax import FluentParser
from fluent.syntax import ast as ftl

from .. import message as msg
from .. import resource as res


@overload
def fluent_parse(
    source: bytes | str | ftl.Resource,
    parse_message: None = None,
) -> res.Resource[ftl.Pattern, str]: ...


@overload
def fluent_parse(
    source: bytes | str | ftl.Resource,
    parse_message: Callable[[ftl.Pattern], msg.Message],
) -> res.Resource[msg.Message, str]: ...


@overload
def fluent_parse(
    source: bytes | str | ftl.Resource,
    parse_message: Callable[[ftl.Pattern], res.V],
) -> res.Resource[res.V, str]: ...


def fluent_parse(
    source: bytes | str | ftl.Resource,
    parse_message: Callable[[ftl.Pattern], res.V] | None = None,
) -> res.Resource[res.V, str]:
    """
    Parse a .ftl file into a message resource.

    Message and term references are represented by `message` function annotations,
    with term identifiers prefixed with a `-`.

    Function names are lower-cased, so e.g. the Fluent `NUMBER` is `number` in the Resource.

    The parsed resource will not include any metadata.
    """

    if isinstance(source, ftl.Resource):
        fluent_res = source
    else:
        source_str = source if isinstance(source, str) else source.decode("utf-8")
        fluent_res = FluentParser().parse(source_str)

    entries: list[res.Entry[res.V, str] | res.Comment] = []
    section = res.Section([], entries)
    resource = res.Resource([section])
    for entry in fluent_res.body:
        if isinstance(entry, ftl.Message) or isinstance(entry, ftl.Term):
            entries.extend(patterns(entry, parse_message))
        elif isinstance(entry, ftl.ResourceComment):
            if entry.content:
                resource.comment = (
                    (resource.comment.rstrip() + "\n\n" + entry.content)
                    if resource.comment
                    else entry.content
                )
        elif isinstance(entry, ftl.GroupComment):
            if entries or section.comment:
                entries = []
                section = res.Section([], entries, comment=entry.content or "")
                resource.sections.append(section)
            else:
                section.comment = entry.content or ""
        elif isinstance(entry, ftl.Comment):
            if entry.content:
                entries.append(res.Comment(entry.content))
        else:  # Junk
            try:
                message = entry.annotations[0].message
            except Exception:
                message = ""
            raise Exception(message or "Fluent parser error")
    return resource


def patterns(
    entry: ftl.Message | ftl.Term, parse_message: Callable[[ftl.Pattern], res.V] | None
) -> Generator[res.Entry[res.V, str], None, None]:
    message = parse_message or (lambda m: cast(res.V, m))
    id = entry.id.name
    if isinstance(entry, ftl.Term):
        id = "-" + id
    comment = entry.comment.content or "" if entry.comment else ""
    if entry.value:
        yield res.Entry(id=[id], value=message(entry.value), comment=comment)
        if comment:
            comment = ""
    for attr in entry.attributes:
        yield res.Entry(
            id=[id, attr.id.name], value=message(attr.value), comment=comment
        )
        if comment:
            comment = ""


def fluent_parse_message(ftl_pattern: ftl.Pattern) -> msg.Message:
    sel_data = find_selectors(ftl_pattern, [])
    selectors = [sd[0] for sd in sel_data]
    filter: list[Key | None] = [None] * len(selectors)
    msg_variants: dict[tuple[Key, ...], msg.Pattern]
    if selectors:
        key_lists = [list(dict.fromkeys(sd[2])) for sd in sel_data]
        for keys in key_lists:
            keys.sort(key=lambda k: (k[2], not k[1]))
        msg_variants = {key: [] for key in product(*key_lists)}
    else:
        msg_variants = {(): []}

    def add_pattern(ftl_pattern: ftl.Pattern) -> None:
        el: (
            ftl.TextElement
            | ftl.Placeable
            | ftl.InlineExpression
            | ftl.SelectExpression
        )
        for el in ftl_pattern.elements:
            while isinstance(el, ftl.Placeable):
                el = el.expression
            if isinstance(el, ftl.SelectExpression):
                msg_sel = next(sd[0] for sd in sel_data if el.selector in sd[1])
                idx = selectors.index(msg_sel)
                prev_filt = filter[idx]
                for v in el.variants:
                    filter[idx] = variant_key(v)
                    add_pattern(v.value)
                filter[idx] = prev_filt
            else:
                for keys, msg_pattern in msg_variants.items():
                    if all(
                        (filt is None or key == filt) for key, filt in zip(keys, filter)
                    ):
                        if isinstance(el, ftl.TextElement):
                            if msg_pattern and isinstance(msg_pattern[-1], str):
                                msg_pattern[-1] += el.value
                            else:
                                msg_pattern.append(el.value)
                        else:
                            msg_pattern.append(inline_expression(el))

    add_pattern(ftl_pattern)

    if selectors:
        variants = {
            tuple(map(message_key, keys)): msg_pattern
            for keys, msg_pattern in msg_variants.items()
            if msg_pattern
        }
        return msg.SelectMessage(selectors, variants)
    else:
        return msg.PatternMessage(next(iter(msg_variants.values())))


Key = tuple[str, bool, bool]
"(name, is_numeric, is_default)"


def variant_key(v: ftl.Variant) -> Key:
    name: str
    is_numeric: bool
    if isinstance(v.key, ftl.Identifier):
        name = v.key.name
        is_numeric = False
    else:
        name = v.key.value
        is_numeric = True
    return (name, is_numeric, v.default)


def message_key(key: Key) -> str | msg.CatchallKey:
    name, _, is_default = key
    return msg.CatchallKey(name) if is_default else name


def find_selectors(
    pattern: ftl.Pattern,
    result: list[tuple[msg.Expression, list[ftl.InlineExpression], list[Key]]],
) -> list[tuple[msg.Expression, list[ftl.InlineExpression], list[Key]]]:
    for el in pattern.elements:
        if isinstance(el, ftl.Placeable) and isinstance(
            el.expression, ftl.SelectExpression
        ):
            ftl_sel = el.expression.selector
            keys = [variant_key(v) for v in el.expression.variants]
            msg_sel = select_expression(ftl_sel, keys)
            prev = next((x for x in result if x[0] == msg_sel), None)
            if prev:
                _, ftl_list, key_list = prev
                ftl_list.append(ftl_sel)
                key_list += keys
            else:
                result.append((msg_sel, [ftl_sel], keys))
            for v in el.expression.variants:
                find_selectors(v.value, result)
    return result


def select_expression(ftl_sel: ftl.InlineExpression, keys: list[Key]) -> msg.Expression:
    plural_categories = ("zero", "one", "two", "few", "many", "other")
    if isinstance(ftl_sel, ftl.VariableReference):
        name = (
            "number"
            if all(
                is_numeric or name in plural_categories for name, is_numeric, _ in keys
            )
            else "string"
        )
        return msg.Expression(
            msg.VariableRef(ftl_sel.id.name), msg.FunctionAnnotation(name)
        )
    elif isinstance(ftl_sel, ftl.StringLiteral):
        return msg.Expression(literal_value(ftl_sel), msg.FunctionAnnotation("string"))
    else:
        return inline_expression(ftl_sel)


def inline_expression(exp: ftl.InlineExpression) -> msg.Expression:
    if isinstance(exp, ftl.NumberLiteral):
        value = exp.value
        return msg.Expression(value, msg.FunctionAnnotation("number"))
    elif isinstance(exp, ftl.StringLiteral):
        value = exp.parse().get("value") or ""
        return msg.Expression(value)
    elif isinstance(exp, ftl.MessageReference):
        name = exp.id.name
        if exp.attribute is not None:
            name += "." + exp.attribute.name
        return msg.Expression(name, msg.FunctionAnnotation("message"))
    elif isinstance(exp, ftl.TermReference):
        name = "-" + exp.id.name
        ftl_named = exp.arguments.named if exp.arguments else []
        return msg.Expression(
            name,
            msg.FunctionAnnotation(
                "message",
                {opt.name.name: literal_value(opt.value) for opt in ftl_named},
            ),
        )
    elif isinstance(exp, ftl.VariableReference):
        name = exp.id.name
        return msg.Expression(msg.VariableRef(name))
    else:  # ftl.FunctionReference
        name = exp.id.name.lower()
        if len(exp.arguments.positional) > 1:
            raise Exception(
                f"Functions with more than one positional argument are not supported: {name}"
            )
        ftl_arg: ftl.Placeable | ftl.InlineExpression | None = next(
            iter(exp.arguments.positional), None
        )
        while isinstance(ftl_arg, ftl.Placeable):
            ftl_arg = cast(ftl.InlineExpression, ftl_arg.expression)
        arg: str | msg.VariableRef | None
        if not ftl_arg:
            arg = None
        elif isinstance(ftl_arg, ftl.NumberLiteral) or isinstance(
            ftl_arg, ftl.StringLiteral
        ):
            arg = literal_value(ftl_arg)
        elif isinstance(ftl_arg, ftl.VariableReference):
            arg = msg.VariableRef(ftl_arg.id.name)
        else:
            raise Exception(f"Unexpected value: {ftl_arg}")
        ftl_named = exp.arguments.named
        return msg.Expression(
            arg,
            msg.FunctionAnnotation(
                name,
                {opt.name.name: literal_value(opt.value) for opt in ftl_named},
            ),
        )


def literal_value(arg: ftl.NumberLiteral | ftl.StringLiteral) -> str:
    return (
        arg.value
        if isinstance(arg, ftl.NumberLiteral)
        else arg.parse().get("value") or ""
    )
