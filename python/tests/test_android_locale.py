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
from moz.l10n.paths import get_android_locale, parse_android_locale

# BCP-47 locale <-> Android locale qualifier, to cover every branch:
# plain, legacy ISO remap (he/id/yi), region (-rXX), and BCP-47 (b+...).
TEST_MAP = [
    ("fr", "fr"),
    ("he", "iw"),  # legacy ISO 639 code
    ("id", "in"),
    ("yi", "ji"),
    ("en-GB", "en-rGB"),  # language + region
    ("he-IL", "iw-rIL"),  # remap + region
    ("sr-Latn", "b+sr+Latn"),  # language + script
    ("zh-Hant-HK", "b+zh+Hant+HK"),  # language + script + region
    ("ca-valencia", "b+ca+valencia"),  # language + variant
    ("he-Latn", "b+iw+Latn"),  # remap inside b+ form
]


def test_get_android_locale(subtests: pytest.Subtests) -> None:
    for locale, expected in TEST_MAP:
        with subtests.test(locale=locale):
            assert get_android_locale(locale) == expected


def test_parse_android_locale(subtests: pytest.Subtests) -> None:
    for expected, alocale in TEST_MAP:
        with subtests.test(alocale=alocale):
            assert parse_android_locale(alocale) == expected


def test_round_trip(subtests: pytest.Subtests) -> None:
    """Test back and forth conversion of android locales."""
    for locale, _ in TEST_MAP:
        with subtests.test(locale=locale):
            assert parse_android_locale(get_android_locale(locale)) == locale


def test_invalid(subtests: pytest.Subtests) -> None:
    """Test values that don't match legacy, region, or b+ qualifier to be rejected."""
    for invalid in ("EN", "e", "en-GB", "en_US", "toolonglang", ""):
        with subtests.test(alocale=invalid):
            assert parse_android_locale(invalid) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
