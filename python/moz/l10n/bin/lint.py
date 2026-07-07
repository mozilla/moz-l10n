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
from enum import Enum
from os.path import relpath, splitext

import click
from moz.l10n.bin.utils import handle_paths, set_log_level
from moz.l10n.formats import UnsupportedFormat, l10n_extensions
from moz.l10n.resource import parse_resource

log = logging.getLogger(__name__)

Result = Enum("Result", ("OK", "SKIP", "UNSUPPORTED", "FAIL"))


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
    "-u",
    "--skip-unknown",
    is_flag=True,
    help="Skip files without a known L10n extension.",
)
@click.argument("paths", nargs=-1)
def cli(
    verbose: int, quiet: bool, config: str, skip_unknown: bool, paths: tuple[str, ...]
) -> None:
    """Lint/validate localization resources.

    If `paths` is a single directory, it is iterated with L10nConfigPaths if --config is set, or L10nDiscoverPaths otherwise.

    If `paths` is not a single directory, its values are treated as glob expressions, with `**` support.

    FIXME: Currently only checks that files can be parsed, and does not check their contents more deeply.
    """
    set_log_level(verbose, quiet)

    res = lint(paths, config_path=config, skip_unknown=skip_unknown)
    sys.exit(res)


def lint(
    file_paths: list[str] | tuple[str, ...],
    *,
    config_path: str | None = None,
    skip_unknown: bool = False,
) -> int:
    """
    Lint/validate `file_paths` localization resources.

    If a single directory is given,
    it is iterated with `L10nConfigPaths` if `config_path` is set,
    or `L10nDiscoverPaths` otherwise.

    If `file_paths` is not a single directory,
    the paths are treated as glob expressions.

    Returns 0 on success, 1 on parse error, or 2 on argument error.
    """
    path_iter, root_dir = handle_paths(config_path, file_paths, log)
    if path_iter is None:
        return 2

    ok = 0
    unsupported = 0
    failed = 0
    for path in path_iter:
        res = lint_file(root_dir, path, skip_unknown)
        if res == Result.SKIP:
            pass
        elif res == Result.UNSUPPORTED:
            unsupported += 1
        elif res == Result.FAIL:
            failed += 1
        else:
            ok += 1
    if not ok and not unsupported and not failed:
        log.warning("Found no localization resources")
    return 1 if failed or unsupported else 0


def lint_file(root: str, path: str, skip_unknown: bool) -> Result:
    """Lint a single file and log accordingly."""
    try:
        log_path = relpath(path, root)
        if log_path.startswith(".."):
            log_path = path
    except ValueError:
        log_path = path
    if skip_unknown and splitext(path)[1] not in l10n_extensions:
        log.info(f"skip {log_path}")
        return Result.SKIP
    try:
        parse_resource(path)
        log.info(f"ok {log_path}")
        return Result.OK
    except (UnsupportedFormat, UnicodeDecodeError):
        log.warning(f"unsupported {log_path}")
        return Result.UNSUPPORTED
    except Exception as error:
        log.warning(f"FAIL {log_path} - {error}")
        return Result.FAIL


if __name__ == "__main__":
    cli()
