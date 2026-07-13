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

import logging
import sys
from collections.abc import Sequence
from enum import Enum
from os.path import abspath, relpath

import click
from moz.l10n.bin.utils import handle_paths, set_log_level
from moz.l10n.formats import UnsupportedFormat
from moz.l10n.resource import parse_resource, serialize_resource

log = logging.getLogger(__name__)

Result = Enum("Result", ("OK", "FIXED", "UNSUPPORTED", "FAIL"))


@click.command()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase logging verbosity. (-v/--verbose INFO, -vv DEBUG).",
)
@click.option("-q", "--quiet", is_flag=True, help="Only log input argument errors.")
@click.option("--config", metavar="PATH", help="Path to l10n.toml config file.")
@click.option(
    "--continue",
    "continue_on_error",
    is_flag=True,
    help="Do not stop at first parse error.",
)
@click.argument("paths", nargs=-1)
def cli(
    verbose: int,
    quiet: bool,
    config: str,
    continue_on_error: bool,
    paths: tuple[str, ...],
) -> None:
    """Fix the formatting for localization resources.

    If `paths` is a single directory, it is iterated with L10nConfigPaths if --config is set, or L10nDiscoverPaths otherwise.

    If `paths` is not a single directory, its values are treated as glob expressions, with `**` support.
    """
    set_log_level(verbose, quiet)

    res = fix(paths, config, continue_on_error)
    sys.exit(res)


def fix(
    file_paths: Sequence[str],
    config_path: str | None = None,
    continue_on_error: bool = False,
) -> int:
    """Fix the formatting for `file_paths` localization resources.

    If a single directory is given,
    it is iterated with `L10nConfigPaths` if `config_path` is set,
    or `L10nDiscoverPaths` otherwise.

    If `file_paths` is not a single directory,
    the paths are treated as glob expressions.

    If `continue_on_error` is not set, operation terminates on the first error.

    Returns 0 on success, 1 on parse error, or 2 on argument error.
    """
    path_iter, root_dir = handle_paths(config_path, file_paths, log)
    if path_iter is None:
        return 2

    fixed = 0
    unsupported = 0
    failed = 0
    total = 0
    for path in path_iter:
        res = fix_file(root_dir, path)
        total += 1
        if res == Result.FIXED:
            fixed += 1
        elif res == Result.UNSUPPORTED:
            unsupported += 1
        elif res == Result.FAIL:
            failed += 1
            if not continue_on_error:
                break

    log.warning("")
    if unsupported > 0:
        log.warning(plural(f"Skipped {unsupported} unsupported file", unsupported))
    touched = total - unsupported
    if touched == 0:
        log.warning("Found no localization resources")
    else:
        log.warning(plural(f"Fixed {fixed}/{touched} file", touched))
    if failed > 0:
        log.warning(plural(f"With {failed} parse failure", failed))
    return 0 if failed == 0 else 1


def fix_file(root: str, path: str) -> Result:
    try:
        rel_path = relpath(path, root)
    except ValueError:
        rel_path = abspath(path)
    try:
        with open(path, "+rb") as file:
            prev = file.read()
            res = parse_resource(path, prev)
            next = bytearray()
            for line in serialize_resource(res):
                next.extend(line.encode("utf-8"))
            if next == prev:
                log.info(f"OK: {rel_path}")
                return Result.OK
            else:
                file.seek(0)
                file.write(next)
                file.truncate()
                log.warning(f"Fixed: {rel_path}")
                return Result.FIXED
    except (UnsupportedFormat, UnicodeDecodeError):
        log.info(f"Skip: {rel_path}")
        return Result.UNSUPPORTED
    except Exception as error:
        log.error(f"FAIL: {rel_path}\n{error}")
        return Result.FAIL


def plural(noun: str, count: int) -> str:
    """Hacky and English-only"""
    return noun if count == 1 else noun + "s"


if __name__ == "__main__":
    cli()
