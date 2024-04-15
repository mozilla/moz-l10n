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

from json import loads
from re import finditer, fullmatch
from typing import Any

from ..message import (
    Declaration,
    Expression,
    Pattern,
    PatternMessage,
    UnsupportedStatement,
    VariableRef,
)
from ..resource import Comment, Entry, Resource, Section


def webext_parse(source: str | bytes) -> Resource[PatternMessage, None]:
    """
    Parse a messages.json file into a message resource.

    Named placeholders are represented as declarations,
    with an attribute used for an example, if it's available.
    """
    json: dict[str, dict[str, Any]] = loads(source)
    entries: list[Entry[PatternMessage, None] | Comment] = []
    for key, msg in json.items():
        src: str = msg["message"]
        comment: str = msg.get("description", "")
        ph_data: dict[str, dict[str, str]] = (
            {k.lower(): v for k, v in msg["placeholders"].items()}
            if "placeholders" in msg
            else {}
        )
        declarations: list[Declaration | UnsupportedStatement] = []
        pattern: Pattern = []
        pos = 0
        for m in finditer(r"\$([a-zA-Z0-9_@]+)\$|(\$[1-9])|\$(\$+)", src):
            text = src[pos : m.start()]
            if text:
                if pattern and isinstance(pattern[-1], str):
                    pattern[-1] += text
                else:
                    pattern.append(text)
            if m[1]:
                # Named placeholder, with content & optional example in placeholders object
                ph = ph_data[m[1].lower()]
                if "_prev" in ph:
                    ph_key = ph["_prev"]
                else:
                    ph_key = m[1]
                    ph_src = ph["content"]
                    ph_value = Expression(
                        VariableRef(ph_src) if fullmatch(r"\$[1-9]", ph_src) else ph_src
                    )
                    if "example" in ph:
                        ph_value.attributes["example"] = ph["example"]
                    declarations.append(Declaration(ph_key, ph_value))
                    ph["_prev"] = ph_key
                pattern.append(Expression(VariableRef(ph_key)))
            elif m[2]:
                # Indexed placeholder
                pattern.append(Expression(VariableRef(m[2])))
            else:
                # Escaped literal dollar sign
                if pattern and isinstance(pattern[-1], str):
                    pattern[-1] += m[3]
                else:
                    pattern.append(m[3])
            pos = m.end()
        if pos < len(src):
            rest = src[pos:]
            if pattern and isinstance(pattern[-1], str):
                pattern[-1] += rest
            else:
                pattern.append(rest)
        entries.append(
            Entry([key], PatternMessage(pattern, declarations), comment=comment)
        )
    return Resource([Section([], entries)])
