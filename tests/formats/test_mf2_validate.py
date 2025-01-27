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

import pytest

from moz.l10n.formats.mf2 import MF2ValidationError, mf2_validate_message
from moz.l10n.message.data import (
    CatchallKey,
    Expression,
    Markup,
    PatternMessage,
    SelectMessage,
    VariableRef,
)


def ok(
    part: Expression | Markup | PatternMessage | SelectMessage | dict[str, Expression],
    exp_decl: list[str] | None = None,
) -> None:
    if isinstance(part, dict):
        mf2_validate_message(PatternMessage(declarations=part, pattern=[]))
        if exp_decl is not None:
            assert list(part.keys()) == exp_decl
    else:
        mf2_validate_message(
            PatternMessage([part])
            if isinstance(part, Expression) or isinstance(part, Markup)
            else part
        )


def fail(
    part: Expression | Markup | PatternMessage | SelectMessage | dict[str, Expression],
) -> None:
    with pytest.raises(MF2ValidationError):
        ok(part)


def test_validate_expression():
    ok(Expression("42"))
    fail(Expression(None))
    fail(Expression(42))

    ok(Expression(VariableRef("var")))
    fail(Expression(VariableRef("-var")))
    fail(Expression(VariableRef(42)))

    ok(Expression(None, "func"))
    ok(Expression("some arg", "func"))
    fail(Expression(None, ""))
    fail(Expression(None, "func badname"))

    ok(Expression(None, "func", {"opt": "some option value"}))
    ok(Expression(None, "func", {"opt": VariableRef("var")}))
    fail(Expression("42", None, {"opt": "42"}))
    fail(Expression("42", "func", "options"))
    fail(Expression("42", "func", ["opt"]))
    fail(Expression(None, "func", {"opt": 42}))
    fail(Expression(None, "func", {42: "opt"}))

    ok(Expression("42", attributes={"attr": True}))
    ok(Expression("42", attributes={"attr": "some attr value"}))
    fail(Expression(None, attributes="attr"))
    fail(Expression(None, attributes=["attr"]))
    fail(Expression(None, attributes={"attr": True}))
    fail(Expression("42", None, attributes={"attr": 42}))
    fail(Expression("42", None, attributes={"attr": VariableRef("var")}))
    fail(Expression("42", None, attributes={42: "attr"}))


def test_validate_markup():
    ok(Markup("open", "name"))
    ok(Markup("standalone", "name"))
    ok(Markup("close", "name"))
    fail(Markup("foo", "name"))
    fail(Markup("open", "bad name"))

    ok(Markup("open", "name", {"opt": "42"}))
    fail(Markup("open", "name", {"opt": 42}))

    ok(Markup("open", "name", attributes={"attr": "x"}))
    ok(Markup("open", "name", {"opt": "42"}, {"attr": "x"}))
    fail(Markup("open", "name", attributes={"attr": 42}))


def test_validate_patternmessage():
    ok(PatternMessage(["pattern"]))
    ok(PatternMessage([Expression(VariableRef("var"))]))
    ok(
        PatternMessage(
            ["first", "second", Expression(VariableRef("var")), Markup("open", "name")]
        )
    )
    fail(PatternMessage("pattern"))
    fail(PatternMessage([42]))
    fail(PatternMessage([Expression(42)]))


def test_validate_declarations():
    ok({})
    ok({"a": Expression("42")})
    ok({"a": Expression(VariableRef("a"))})
    ok({"a": Expression(VariableRef("b"))})
    ok({"a": Expression("42", "func", {"o": VariableRef("b")})})
    fail({42: Expression("a")})

    fail(PatternMessage(declarations="decl", pattern=[]))
    fail(PatternMessage(declarations=["decl"], pattern=[]))

    ok({"a": Expression(VariableRef("a")), "b": Expression(VariableRef("a"))})
    ok(
        {"b": Expression("42"), "a": Expression("42")},
        ["a", "b"],
    )
    ok(
        {"a": Expression("42"), "b": Expression(VariableRef("b"))},
        ["b", "a"],
    )
    ok(
        {"a": Expression(VariableRef("b")), "b": Expression(VariableRef("b"))},
        ["b", "a"],
    )

    ok(
        {
            "a": Expression(VariableRef("b")),
            "b": Expression(VariableRef("c")),
            "c": Expression("42"),
        },
        ["c", "b", "a"],
    )
    ok(
        {
            "a": Expression("42", "func", {"o": VariableRef("b")}),
            "c": Expression("42"),
            "b": Expression("42"),
        },
        ["b", "a", "c"],
    )
    ok(
        {
            "a": Expression(
                "42", "func", {"o1": VariableRef("b"), "o2": VariableRef("c")}
            ),
            "c": Expression("42"),
            "b": Expression("42"),
        },
        ["b", "c", "a"],
    )

    fail({"a": Expression("42", "func", {"o": VariableRef("a")})})
    fail({"a": Expression(VariableRef("b")), "b": Expression(VariableRef("a"))})
    fail(
        {
            "a": Expression(VariableRef("b")),
            "b": Expression(VariableRef("c")),
            "c": Expression(VariableRef("a")),
        }
    )
    fail(
        {
            "c": Expression(VariableRef("a")),
            "b": Expression(VariableRef("c")),
            "a": Expression(VariableRef("b")),
        }
    )


def test_validate_selectmessage():
    ok(
        SelectMessage(
            declarations={"var": Expression("42", "func")},
            selectors=(VariableRef("var"),),
            variants={(CatchallKey(),): ["variant"]},
        )
    )
    ok(
        SelectMessage(
            declarations={"var": Expression("42", "func")},
            selectors=(VariableRef("var"), VariableRef("var")),
            variants={(CatchallKey(), CatchallKey()): ["variant"]},
        )
    )

    # No selectors
    fail(
        SelectMessage(
            declarations={},
            selectors=(),
            variants={(): ["variant"]},
        )
    )

    # Bad declarations
    fail(
        SelectMessage(
            declarations=[],
            selectors=(VariableRef("var"),),
            variants={(CatchallKey(),): ["variant"]},
        )
    )

    # Bad selectors
    fail(
        SelectMessage(
            declarations={"var": Expression("42", "func")},
            selectors=[VariableRef("var")],
            variants={(CatchallKey(),): ["variant"]},
        )
    )

    # Bad variants
    fail(
        SelectMessage(
            declarations={"var": Expression("42", "func")},
            selectors=(VariableRef("var"),),
            variants=[],
        )
    )

    # Bad variant key
    fail(
        SelectMessage(
            declarations={"var": Expression("42", "func")},
            selectors=(VariableRef("var"),),
            variants={(42,): ["bad key"], (CatchallKey(),): ["catchall"]},
        )
    )

    # No selector declaration
    fail(
        SelectMessage(
            declarations={},
            selectors=(VariableRef("var"),),
            variants={(CatchallKey(),): ["variant"]},
        )
    )

    # No selector function
    fail(
        SelectMessage(
            declarations={"var": Expression("42")},
            selectors=(VariableRef("var"),),
            variants={(CatchallKey(),): ["variant"]},
        )
    )

    # No variants
    fail(
        SelectMessage(
            declarations={"var": Expression("42", "func")},
            selectors=(VariableRef("var"),),
            variants={},
        )
    )

    # No fallback variant
    fail(
        SelectMessage(
            declarations={"var": Expression("42", "func")},
            selectors=(VariableRef("var"),),
            variants={("key",): ["variant"]},
        )
    )

    # Variant key mismatch
    fail(
        SelectMessage(
            declarations={"var": Expression("42", "func")},
            selectors=(VariableRef("var"), VariableRef("var")),
            variants={(CatchallKey(),): ["variant"]},
        )
    )

    # No fallback variant
    fail(
        SelectMessage(
            declarations={"var": Expression("42", "func")},
            selectors=(VariableRef("var"), VariableRef("var")),
            variants={(CatchallKey(), "key"): ["variant"]},
        )
    )

    # Variant key mismatch
    fail(
        SelectMessage(
            declarations={"var": Expression("42", "func")},
            selectors=(VariableRef("var"),),
            variants={(CatchallKey(), CatchallKey()): ["variant"]},
        )
    )

    ok(
        SelectMessage(
            declarations={
                "var1": Expression("42", "func"),
                "var2": Expression(VariableRef("var1")),
            },
            selectors=(VariableRef("var2"),),
            variants={("key",): ["variant"], (CatchallKey(),): ["catchall"]},
        )
    )

    # No selector function
    fail(
        SelectMessage(
            declarations={
                "var1": Expression("42"),
                "var2": Expression(VariableRef("var1")),
            },
            selectors=(VariableRef("var2"),),
            variants={(CatchallKey(),): ["variant"]},
        )
    )
