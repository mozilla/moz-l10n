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
from importlib.util import module_from_spec, spec_from_file_location
from os.path import abspath
from traceback import format_exc

import click
from moz.l10n.bin.utils import set_log_level
from moz.l10n.migrate import all_migrations
from moz.l10n.paths.android_locale import get_android_locale
from moz.l10n.paths.config import L10nConfigPaths
from moz.l10n.paths.discover import L10nDiscoverPaths, MissingSourceDirectoryError

log = logging.getLogger(__name__)

Result = Enum("Result", ("OK", "SKIP", "UNSUPPORTED", "FAIL"))


@click.command()
@click.option("-v", "--verbose", count=True, help="Set logging verbosity")
@click.option("-q", "--quiet", is_flag=True, help="Only log input argument errors")
@click.option(
    "-n", "--dry-run", is_flag=True, help="Do not apply changes to file system"
)
@click.option("--config", metavar="PATH", help="Path to l10n.toml config file")
@click.option(
    "--root",
    metavar="PATH",
    type=str,
    help="Path to localization root, if --config is not set",
)
@click.option(
    "--ref",
    metavar="PATH",
    type=str,
    help="Path to localization reference root, if separate from --root",
)
@click.argument("migration", nargs=-1, required=True)
def cli(
    verbose: int,
    quiet: bool,
    dry_run: bool,
    config: str,
    root: str,
    ref: str,
    migration: tuple[str],
) -> None:
    """
    Apply migrations to localization resources.

    Returns 0 on success, 1 on internal error, or 2 on argument error.
    """
    set_log_level(verbose, quiet)

    try:
        apply_migrations(
            migration,
            config_path=config,
            discover_root=root,
            discover_ref_root=ref,
            dry_run=dry_run,
        )
    except MissingSourceDirectoryError:
        log.error(f"Reference root not found in {ref or root}")
        log.debug(format_exc())
        sys.exit(2)
    except ValueError as err:
        log.error(str(*err.args))
        log.debug(format_exc())
        sys.exit(2)
    except Exception:
        log.warning(format_exc())
        sys.exit(1)


def apply_migrations(
    migration_paths: list[str] | tuple[str],
    *,
    config_path: str | None = None,
    discover_root: str | None = None,
    discover_ref_root: str | None = None,
    dry_run: bool = False,
) -> None:
    paths: L10nConfigPaths | L10nDiscoverPaths | None = None
    if config_path:
        if discover_root:
            raise ValueError("--config and --root must not be both set.")
        paths = L10nConfigPaths(
            config_path, locale_map={"android_locale": get_android_locale}
        )
    elif discover_root:
        if discover_ref_root is not None:
            discover_ref_root = abspath(discover_ref_root)
        paths = L10nDiscoverPaths(abspath(discover_root), ref_root=discover_ref_root)

    all_migrations.clear()
    for idx, migration_path in enumerate(migration_paths):
        name = f"migration_{idx}"
        spec = spec_from_file_location(name, migration_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Loading {migration_path} failed")
        module = module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as err:
            raise ValueError(f"Loading {migration_path} failed") from err
    if not all_migrations:
        raise ValueError("No migrations found")

    for migration in all_migrations:
        if paths is not None:
            migration.set_paths(paths)
        migration.apply(dry_run=dry_run)


if __name__ == "__main__":
    cli()
