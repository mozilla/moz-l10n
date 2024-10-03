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
from collections import defaultdict
from os import makedirs
from os.path import dirname, exists, join, relpath
from shutil import copyfile
from textwrap import dedent

from moz.l10n.message import Message
from moz.l10n.paths.config import L10nConfigPaths
from moz.l10n.resource import UnsupportedResource, parse_resource, serialize_resource
from moz.l10n.resource.data import Comment, Entry, Resource, Section
from moz.l10n.resource.format import Format

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

    cfg_path: str = args.config
    l10n_base: str = args.base
    l10n_target: str = args.target
    locales: set[str] = set(args.locales)

    # locale -> [ftl_filtered, l10n_fallback]
    msg_data: dict[str, list[int]] = defaultdict(lambda: [0, 0])

    paths = L10nConfigPaths(cfg_path)
    paths.base = l10n_base
    paths.locales = None
    for (source_path, l10n_path_template), path_locales in paths.all().items():
        log.debug(f"source {source_path}")
        try:
            source = parse_resource(source_path)
        except UnsupportedResource:
            source = None
        for locale in locales.intersection(path_locales) if path_locales else locales:
            l10n_path = l10n_path_template.format(locale=locale)
            rel_path = relpath(l10n_path, l10n_base)
            tgt_path = join(l10n_target, rel_path)
            makedirs(dirname(tgt_path), exist_ok=True)
            if source:
                msg_delta = write_target_file(rel_path, source, l10n_path, tgt_path)
                if msg_delta < 0:
                    msg_data[locale][0] -= msg_delta
                elif msg_delta > 0:
                    msg_data[locale][1] += msg_delta
                else:
                    msg_data[locale]
            elif exists(l10n_path):
                if l10n_base != l10n_target:
                    log.info(f"copy {rel_path}")
                    copyfile(l10n_path, tgt_path)
                else:
                    log.info(f"skip {rel_path}")
            else:
                log.info(f"skip {rel_path}")

    log.info("----")
    for locale, (ftl_missing, l10n_fallback) in sorted(
        msg_data.items(), key=lambda d: d[0]
    ):
        log.info(f"{locale}:")
        log.info(f"  missing_ftl {ftl_missing:>6}")
        log.info(f"  fallback    {l10n_fallback:>6}")


def write_target_file(
    name: str,
    source_res: Resource[Message, str],
    l10n_path: str,
    tgt_path: str,
) -> int:
    l10n_res = parse_resource(l10n_path) if exists(l10n_path) else None

    if source_res.format == Format.fluent:
        # Fluent uses per-message fallback at runtime, allowing resources to be incomplete.
        # Therefore, build result by filtering out any content not in the source.
        if l10n_res is None:
            msg_delta = -sum(
                sum(1 for entry in section.entries if isinstance(entry, Entry))
                for section in source_res.sections
            )
            log.info(f"create empty {name} ({msg_delta})")
            open(tgt_path, "a").close()
            return msg_delta

        source_map = _message_map(name, source_res)
        msg_delta = 0
        for section in l10n_res.sections:
            msg_delta -= len(section.entries)
            section.entries = [
                entry
                for entry in section.entries
                if isinstance(entry, Entry) and section.id + entry.id in source_map
            ]
            msg_delta += len(section.entries)
        msg = f"filter {name}"
        log.info(f"{msg} ({msg_delta})" if msg_delta != 0 else msg)
        with open(tgt_path, "w") as file:
            for line in serialize_resource(l10n_res, trim_comments=True):
                file.write(line)
        return msg_delta

    # For other formats, build result from source,
    # using any localized messages that are available.
    if l10n_res is None:
        l10n_map = {}
        l10n_res = Resource(source_res.format, [])
    else:
        l10n_map = _message_map(l10n_path, l10n_res)
        l10n_res.sections = []
    msg_delta = 0

    def get_entry(
        section_id: tuple[str, ...], source_entry: Entry[Message, str]
    ) -> Entry[Message, str] | Comment:
        id = section_id + source_entry.id
        if id in l10n_map:
            return l10n_map[id]
        else:
            nonlocal msg_delta
            msg_delta += 1
            return source_entry

    for section in source_res.sections:
        tgt_entries = [
            get_entry(section.id, entry)
            for entry in section.entries
            if isinstance(entry, Entry)
        ]
        l10n_res.sections.append(Section(section.id, tgt_entries))
    msg = f"fill {name}"
    log.info(f"{msg} (+{msg_delta})" if msg_delta != 0 else msg)
    with open(tgt_path, "w") as file:
        for line in serialize_resource(l10n_res, trim_comments=True):
            file.write(line)
    return msg_delta


def _message_map(
    path: str,
    resource: Resource[Message, str],
) -> dict[tuple[str, ...], Entry[Message, str]]:
    if path in _message_id_map_cache:
        return _message_id_map_cache[path]
    else:
        id_map = _message_id_map_cache[path] = {
            section.id + entry.id: entry
            for section in resource.sections
            for entry in section.entries
            if isinstance(entry, Entry)
        }
        return id_map


_message_id_map_cache: dict[str, dict[tuple[str, ...], Entry[Message, str]]] = {}

if __name__ == "__main__":
    cli()
