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

import os
from collections.abc import Iterator
from os.path import isdir, join, relpath

from gitignorant import check_match, parse_gitignore_file

from ..message import Message
from .data import Resource
from .parse_resource import parse_resource


def iter_resources(
    root: str, dirs: list[str] | None = None, ignorepath: str = ".l10n-ignore"
) -> Iterator[tuple[str, Resource[Message, str] | None]]:
    """
    Iterate through localizable resources under the `root` directory.
    Use `dirs` to limit the search to only some subdirectories under `root`.

    Yields `(str, Resource | None)` tuples,
    with the file path and the corresponding `Resource`,
    or `None` for files that could not be parsed as localization resources.

    To ignore files, include a `.l10n-ignore` file in `root`,
    or some other location passed in as `ignorepath`.
    This file uses git-ignore syntax,
    and is always based in the `root` directory.
    """
    if not isdir(root):
        raise ValueError(f"Not a directory: {root}")
    try:
        with open(join(root, ignorepath), encoding="utf-8") as file:
            ignore = list(parse_gitignore_file(file))
    except OSError:
        ignore = None
    for dir in (join(root, p) for p in dirs) if dirs else (root,):
        for dirpath, dirnames, filenames in os.walk(dir):
            if ignore:
                idx = len(dirnames) - 1
                while idx >= 0:
                    rp = relpath(join(dirpath, dirnames[idx]), start=root)
                    if os.sep != "/":
                        rp = rp.replace(os.sep, "/")
                    if ignore and check_match(ignore, rp, is_dir=True):
                        del dirnames[idx]
                    idx -= 1
            for fn in filenames:
                path = join(dirpath, fn)
                if ignore:
                    rp = relpath(path, start=root)
                    if os.sep != "/":
                        rp = rp.replace(os.sep, "/")
                    if check_match(ignore, rp):
                        continue
                try:
                    yield (path, parse_resource(path))
                except ValueError:
                    yield (path, None)
