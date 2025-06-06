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
from json import dumps
from re import sub
from typing import Any

from ...model import (
    Entry,
    Expression,
    Message,
    PatternMessage,
    Resource,
    VariableRef,
)


def webext_serialize(
    resource: Resource[str] | Resource[Message],
    trim_comments: bool = False,
) -> Iterator[str]:
    """
    Serialize a resource as the contents of a messages.json file.

    Section identifiers and multi-part message identifiers are not supported.
    Resource and section comments are not supported.
    Metadata is not supported.

    Yields the entire JSON result as a single string.
    """

    def check(comment: str | None, meta: Any) -> None:
        if trim_comments:
            return
        if comment:
            raise ValueError("Resource and section comments are not supported")
        if meta:
            raise ValueError("Metadata is not supported")

    check(resource.comment, resource.meta)
    res: dict[str, Any] = {}
    for section in resource.sections:
        if section.id:
            raise ValueError(f"Section identifiers not supported: {section.id}")
        check(section.comment, section.meta)
        for entry in section.entries:
            if isinstance(entry, Entry):
                check(None, entry.meta)
                if len(entry.id) != 1:
                    raise ValueError(f"Unsupported entry identifier: {entry.id}")
                name = entry.id[0]
                if isinstance(entry.value, str):
                    res[name] = {"message": entry.value}
                    if not trim_comments and entry.comment:
                        res[name]["description"] = entry.comment
                elif isinstance(entry.value, PatternMessage):
                    try:
                        msgstr, placeholders = webext_serialize_message(
                            entry.value, trim_comments=trim_comments
                        )
                    except ValueError as err:
                        raise ValueError(f"Error serializing {name}") from err
                    msg: dict[str, Any] = {"message": msgstr}
                    if not trim_comments and entry.comment:
                        msg["description"] = entry.comment
                    if placeholders:
                        msg["placeholders"] = placeholders
                    res[name] = msg
                else:
                    raise ValueError(f"Unsupported entry for {name}: {entry.value}")
            else:
                check(entry.comment, None)
    yield dumps(res, indent=2, ensure_ascii=False)
    yield "\n"


def webext_serialize_message(
    msg: Message, *, trim_comments: bool = False
) -> tuple[str, dict[str, Any]]:
    """
    Serialize a message in its messages.json representation.

    Returns a tuple consisting of the `"message"` string
    and a `"placeholders"` object.
    """

    if not isinstance(msg, PatternMessage):
        raise ValueError(f"Unsupported message: {msg}")
    msgstr = ""
    placeholders: dict[str, Any] = {}
    for part in msg.pattern:
        if isinstance(part, str):
            msgstr += sub(r"\$+", r"$\g<0>", part)
        elif (
            isinstance(part, Expression)
            and isinstance(part.arg, VariableRef)
            and part.function is None
        ):
            ph_name = part.arg.name
            source = part.attributes.get("source", None)
            local = msg.declarations.get(ph_name, None)
            if local:
                local_source = local.attributes.get("source", None)
                if isinstance(local_source, str):
                    content = local_source
                elif isinstance(local.arg, VariableRef):
                    content = local.arg.name
                    if not content.startswith("$"):
                        content = f"${content}"
                elif isinstance(local.arg, str):
                    content = local.arg
                else:
                    raise ValueError(f"Unsupported placeholder for {ph_name}: {local}")
                if local.function:
                    raise ValueError(f"Unsupported annotation for {ph_name}: {local}")
                if (
                    isinstance(source, str)
                    and len(source) >= 3
                    and source.startswith("$")
                    and source.endswith("$")
                ):
                    ph_name = source[1:-1]
                else:
                    source = None
                if not any(key.lower() == ph_name.lower() for key in placeholders):
                    placeholders[ph_name] = {"content": content}
                    example = (
                        None if trim_comments else local.attributes.get("example", None)
                    )
                    if isinstance(example, str):
                        placeholders[ph_name]["example"] = example
                    elif example:
                        raise ValueError(
                            f"Unsupported placeholder example for {ph_name}: {example}"
                        )
                msgstr += source or f"${ph_name}$"
            else:
                arg_name = source if isinstance(source, str) else ph_name
                msgstr += arg_name if arg_name.startswith("$") else f"${arg_name}"
        else:
            raise ValueError(f"Unsupported message part: {part}")
    return msgstr, placeholders
