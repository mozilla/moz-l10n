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
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from os import makedirs
from os.path import dirname, exists, join, relpath
from shutil import copyfile
from textwrap import dedent

from moz.l10n.paths.config import L10nConfigPaths
from moz.l10n.resource import UnsupportedResource, parse_resource, serialize_resource
from moz.l10n.resource.data import Entry

log = logging.getLogger(__name__)


def cli() -> None:
    parser = ArgumentParser(
        description=dedent(
            """
            Build localization files for release.

            Iterates source files as defined by --config, reads localization sources from --base, and writes to --target.

            Trims out all comments and messages not in the source files for each of the --locales.

            Adds empty files for any missing from the target locale.
            """
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="increase logging verbosity"
    )
    parser.add_argument(
        "--config", metavar="PATH", required=True, help="l10n.toml config file"
    )
    parser.add_argument(
        "--base", metavar="PATH", required=True, help="base dir for localizations"
    )
    parser.add_argument(
        "--target", metavar="PATH", required=True, help="target dir for localizations"
    )
    parser.add_argument(
        "--locales", metavar="LOCALE", nargs="+", required=True, help="target locales"
    )
    args = parser.parse_args()

    log_level = (
        logging.WARNING
        if args.verbose == 0
        else logging.INFO if args.verbose == 1 else logging.DEBUG
    )
    logging.basicConfig(format="%(message)s", level=log_level)

    build_targets_for_release(args.config, args.base, args.target, set(args.locales))


def build_targets_for_release(
    cfg_path: str, l10n_base: str, l10n_target: str, locales: set[str]
) -> None:
    paths = L10nConfigPaths(cfg_path)
    paths.base = l10n_base
    paths.locales = None
    for (source_path, l10n_path_template), path_locales in paths.all().items():
        log.debug(f"source {source_path}")
        try:
            source = parse_resource(source_path)
            source_ids = set(
                section.id + entry.id
                for section in source.sections
                for entry in section.entries
                if isinstance(entry, Entry)
            )
        except UnsupportedResource:
            source_ids = None
        for locale in locales.intersection(path_locales) if path_locales else locales:
            l10n_path = l10n_path_template.format(locale=locale)
            rel_path = relpath(l10n_path, l10n_base)
            tgt_path = join(l10n_target, rel_path)
            makedirs(dirname(tgt_path), exist_ok=True)
            if exists(l10n_path):
                if source_ids:
                    msg_delta = 0
                    res = parse_resource(l10n_path)
                    for section in res.sections:
                        msg_delta -= len(section.entries)
                        section.entries = [
                            entry
                            for entry in section.entries
                            if not isinstance(entry, Entry)
                            or section.id + entry.id in source_ids
                        ]
                        msg_delta += len(section.entries)
                    msg = f"filter {rel_path}"
                    log.info(f"{msg} ({msg_delta})" if msg_delta != 0 else msg)
                    with open(tgt_path, "w") as file:
                        for line in serialize_resource(res, trim_comments=True):
                            file.write(line)
                elif l10n_base != l10n_target:
                    log.info(f"copy {rel_path}")
                    copyfile(l10n_path, tgt_path)
                else:
                    log.info(f"skip {rel_path}")
            elif source_ids:
                log.info(f"create empty {rel_path}")
                open(tgt_path, "a").close()
            else:
                log.info(f"skip {rel_path}")


if __name__ == "__main__":
    cli()
