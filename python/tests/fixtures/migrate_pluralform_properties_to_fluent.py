# Used by test_firefox_plural_properties in python/tests/test_migrate.py

import re
from typing import cast

from moz.l10n.migrate import Migrate
from moz.l10n.migrate.utils import MigrationContext, get_entry
from moz.l10n.model import (
    CatchallKey,
    Expression,
    PatternMessage,
    SelectMessage,
    VariableRef,
)


def parse_pattern(src: str):
    pos = 0
    for m in re.finditer(r"#1|#2|%d", src):
        start = m.start()
        if start > pos:
            yield src[pos:start]
        yield Expression(VariableRef("n" if m[0] == "#1" else "x"))
        pos = m.end()
    if pos < len(src):
        yield src[pos:]


def get_key(locale: str, idx: int):
    if locale in {"ltg", "lv"}:
        categories = ["zero", "one", CatchallKey("other")]
    elif locale in {"bs", "hr", "lt", "ro", "sr"}:
        categories = ["one", "few", CatchallKey("other")]
    elif locale in {"be", "cs", "pl", "ru", "sk", "szl", "uk"}:
        categories = ["one", "few", CatchallKey("many")]
    elif locale in {"dsb", "gd", "hsb", "sl"}:
        categories = ["one", "two", "few", CatchallKey("other")]
    elif locale in {"br", "ga"}:
        categories = ["one", "two", "few", "many", CatchallKey("other")]
    elif locale == "ar":
        categories = ["one", "two", "few", "many", CatchallKey("other"), "zero"]
    elif locale == "cy":
        categories = ["zero", "one", "two", "few", "many", CatchallKey("other")]
    else:
        categories = ["one", CatchallKey("other")]
    return categories[idx if idx < len(categories) else -1]


plural_categories = ["zero", "one", "two", "few", "many", "other"]


def plural(ref_path: str, id: str):
    def plural_(_, ctx: MigrationContext):
        res = ctx.get_resource(ref_path)
        if res is None:
            return None
        entry = get_entry(res, id)
        if entry is None:
            return None
        pattern = cast(PatternMessage, entry.value).pattern
        assert len(pattern) == 1
        assert isinstance(pattern[0], str)
        parts = pattern[0].split(";")

        if len(parts) > 1:
            var_list = [
                (get_key(ctx.locale, idx), part) for idx, part in enumerate(parts)
            ]
            var_list.sort(
                key=lambda v: plural_categories.index(k)
                if isinstance(k := v[0], str) and k in plural_categories
                else 6
            )
            entry.value = SelectMessage(
                {"n": Expression(VariableRef("n"), "number")},
                (VariableRef("n"),),
                {(key,): list(parse_pattern(part)) for key, part in var_list},
            )

        entry.comment = re.sub(
            r"LOCALIZATION NOTE.*?:|Semi-colon list of plural forms.|See: http.*?/Localization_and_Plurals",
            "",
            entry.comment,
        ).strip()

        return (entry, {id})

    return plural_


Migrate(
    {
        "debugger.ftl": {
            "source-search-results-summary": plural(
                "debugger.properties", "sourceSearch.resultsSummary2"
            ),
            "editor-search-results": plural(
                "debugger.properties", "editor.searchResults1"
            ),
        }
    }
)
