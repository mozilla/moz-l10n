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
from os.path import abspath, basename, dirname, isdir, join, normpath, relpath
from typing import Collection

import click
from moz.l10n.bin.utils import set_log_level
from moz.l10n.formats import UnsupportedFormat
from moz.l10n.model import Entry
from moz.l10n.paths import L10nConfigPaths, L10nDiscoverPaths
from moz.l10n.resource import parse_resource


def _ext_settify(
    context: click.Context, param: click.Parameter, value: str | None
) -> tuple[set[str], set[str]]:
    """Help turning comma separated extenstions string into proprerly stripped sets.
    Sorting into include and exclude sets according to `!`-prefix.
    Ensuring `.` prefixing each extension.
    """
    ext_include: set[str] = set()
    ext_exclude: set[str] = set()
    value = None if value is None else value.strip("\"'")
    if not value:
        return ext_include, ext_exclude

    for item in value.split(","):
        item = item.strip()
        exclude = item.startswith("!")
        if exclude:
            item = item[1:]

        if not item:
            continue

        if not item.startswith("."):
            item = f".{item}"

        if exclude:
            ext_exclude.add(item)
        else:
            ext_include.add(item)

    return ext_include, ext_exclude


@click.command()
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase logging verbosity. (-v/--verbose INFO, -vv DEBUG).",
)
@click.option("--json", "json_output", is_flag=True, help="Output JSON.")
@click.option(
    "--ext",
    help="File extension(s). Separate multiple by comma (`ini,ftl`). Prefix with ! to exclude (`!json`).",
    type=str,
    callback=_ext_settify,
)
@click.option(
    "--source",
    metavar="PATH",
    required=True,
    type=str,
    help="Path to source file listing expected files & messages.",
)
def cli(
    paths: tuple[str, ...],
    source: str,
    verbose: int,
    ext: tuple[set[str], set[str]],
    *,
    json_output: bool = False,
) -> None:
    """Compare localizations to their `source` and get a report.

    Source may be:
    - a directory (using `L10nDiscoverPaths`),
    - a TOML config file (using `L10nConfigPaths`), or
    - a JSON file containing a mapping of file paths to arrays of messages.
    """
    set_log_level(verbose)

    ext_include, ext_exclude = ext

    def ext_filter(path: str) -> bool:
        included = not ext_include or any(path.endswith(ext) for ext in ext_include)
        excluded = ext_exclude and any(path.endswith(ext) for ext in ext_exclude)
        return included and not excluded

    if source.endswith(".json"):
        with open(source) as f:
            source_data: dict[str, Collection[str]] = json.load(f)
        if ext_include or ext_exclude:
            source_data = {k: set(v) for k, v in source_data.items() if ext_filter(k)}
    else:
        source_paths: L10nConfigPaths | L10nDiscoverPaths = (
            L10nConfigPaths(source)
            if source.endswith(".toml")
            else L10nDiscoverPaths(source, source)
        )
        path0 = abspath(paths[0])
        locale0 = basename(path0)
        source_paths.base = dirname(path0)
        source_data = {}
        for ref_path, tgt_path in source_paths.all():
            if ext_filter(tgt_path):
                try:
                    path = relpath(tgt_path.format(locale=locale0), path0)
                    source_data[path] = msg_ids(ref_path)
                except UnsupportedFormat:
                    continue
    source_total = sum(len(sd) for sd in source_data.values())
    if source_total == 0:
        raise ValueError(f"No messages found for source {source}")
    if not json_output:
        print(f"source: {source_total}")

    json_res = {}
    for path in paths:
        if not isdir(path):
            continue
        lc = basename(normpath(path))
        errors, missing = compare(source_data, path)
        if json_output:
            json_res[lc] = {
                "errors": errors or None,
                "missing": missing or None,
            }
        else:
            total = sum(len(rm) for rm in missing.values())
            print(f"{lc}: {-total}")
            for path, error in errors.items():
                print(f"  !!! {path}: {error}")
            if verbose > 0:
                for path, messages in missing.items():
                    print(f"  {path}: {-len(messages)}")
                    if verbose > 1:
                        for msg in messages:
                            print(f"    {msg}")

    if json_output:
        print(json.dumps(json_res, ensure_ascii=False))


def compare(
    source_data: dict[str, Collection[str]], root: str
) -> tuple[dict[str, str], dict[str, list[str]]]:
    errors: dict[str, str] = {}
    missing: dict[str, list[str]] = {}
    for path, src_messages in source_data.items():
        if src_messages:
            try:
                tgt_messages = msg_ids(join(root, path))
                for msg in src_messages:
                    if msg not in tgt_messages:
                        if path in missing:
                            missing[path].append(msg)
                        else:
                            missing[path] = [msg]
            except FileNotFoundError:
                missing[path] = list(src_messages)
            except Exception as e:
                errors[path] = str(e)
    return errors, missing


def msg_ids(path: str) -> Collection[str]:
    res = parse_resource(path)
    return {
        ".".join(section.id + entry.id)
        for section in res.sections
        for entry in section.entries
        if isinstance(entry, Entry)
    }


if __name__ == "__main__":
    cli()
