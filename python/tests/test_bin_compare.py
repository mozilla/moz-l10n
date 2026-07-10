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

import json
import sys
from contextlib import redirect_stdout
from io import StringIO
from os.path import join
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest.mock import patch

from moz.l10n.bin.compare import cli

from .utils import Tree, build_file_tree


def test_cli_android_locale_template() -> None:
    """Test `{android_locale}` target template to resolve via default
    locale map including the legacy ISO remap "he" -> "iw".
    (Used to crash with KeyError: 'android_locale')
    """
    cfg_toml = dedent(
        """
        basepath = "."
        [[paths]]
            reference = "en/file.ftl"
            l10n = "{android_locale}/file.ftl"
        """
    )
    tree: Tree = {
        "l10n.toml": cfg_toml,
        "en": {"file.ftl": "msg-a = src\nmsg-b = src\nmsg-c = src\n"},
        # "he" translations live under Android locale dir name ("iw"):
        "iw": {"file.ftl": "msg-a = he\n"},
        # while compared path is BCP-47 locale dir:
        "he": {},
    }
    with TemporaryDirectory() as root:
        build_file_tree(root, tree)
        # fmt: off
        argv = ["l10n-compare",
            join(root, "he"),
            "--source", join(root, "l10n.toml"),
            "--json",
        ]
        # fmt: on
        out = StringIO()
        with patch.object(sys, "argv", argv), redirect_stdout(out):
            cli()
        result = json.loads(out.getvalue())

    assert list(result.keys()) == ["he"]
    assert result["he"]["errors"] is None
    missing = sorted(m for ids in result["he"]["missing"].values() for m in ids)
    assert missing == ["msg-b", "msg-c"]


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
