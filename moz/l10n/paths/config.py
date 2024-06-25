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

import sys
from collections.abc import Callable, Iterator
from glob import glob
from os import sep
from os.path import dirname, isfile, join, normpath, relpath
from re import Pattern, compile
from typing import Any, Dict

if sys.version_info >= (3, 11):
    from tomllib import load
else:
    from tomli import load

path_stars = compile(r"[*]([*]([/\\][*]*)?)?")
path_var = compile(r"{(\w+)}")


def path_regex(path: str) -> Pattern[str]:
    """
    Captures * groups as indexed and {vars} as named.
    Expects `path` to use `/` as separator.
    """
    path = path_stars.sub(
        lambda m: (
            "([^/]*)" if m[0] == "*" else "((?:.*/)?)" if m[0] == "**/" else "(.*)"
        ),
        path,
    )
    path = path_var.sub(r"(?P<\1>[^/]*)", path)
    return compile(path)


class PartialMap(Dict[str, str]):
    """Allows `str.format_map()` calls with partial values."""

    def __missing__(self, key: str) -> str:
        return "{" + str(key) + "}"


class L10nConfigPaths:
    """
    Wrapper for localization config files.

    Supports a subset of the format specified at:
    https://moz-l10n-config.readthedocs.io/en/latest/fileformat.html

    Differences:
    - `[build]` is ignored
    - `[[excludes]]` are not supported
    - `[[filters]]` are ignored
    - `[[paths]]` must always include both `reference` and `l10n`

    Does not consider `.l10n-ignore` files.
    """

    base: str
    """
    The configuration root,
    determined in the TOML by `basepath` relative to the config file path
    or set by the user.
    """
    locales: list[str] | None
    """
    Locales for the config,
    determined in the TOML by `locales` or set directly by the user.
    """

    def __init__(
        self,
        cfg_path: str,
        cfg_load: Callable[[str], dict[str, Any]] | None = None,
        locale_map: dict[str, Callable[[str], str]] | None = None,
        _seen: set[str] | None = None,
    ) -> None:
        """
        To customize the loading of a configuration at `cfg_path`, set `cfg_load`.

        As configurations may include others, `cfg_load` can get called multiple times.
        `_seen` is used internally to deduplicate file loads.

        To use custom path variables for locales,
        set `locale_map` to be a mapping of path variable names to functions,
        which will be called with `locale` as their only argument.
        """
        if cfg_load:
            toml = cfg_load(cfg_path)
        else:
            with open(cfg_path, mode="rb") as file:
                toml = load(file)
        self._cfg_path = cfg_path
        self._locale_map = locale_map or {}
        base = toml.get("basepath", ".")
        self.base = normpath(join(dirname(cfg_path), base))
        self._ref_root = self.base
        self.locales = toml.get("locales", None)
        env = toml.get("env", None)
        env_map = PartialMap(env) if env else None

        self._templates: list[tuple[str, Pattern[str]]] = []  #
        """
        `[(ref, target)]`

        To find references for targets,
        retains a `ref` string with `{}` slots for the corresponding
        `*` and `**` parts of the template paths,
        which are also the indexed groups captured in `target`.
        """

        # ref -> (target, locales)
        self._path_data: dict[str, tuple[str, list[str] | None]] = {}
        for path in toml.get("paths", []):
            ref: str = normpath(join(self._ref_root, path["reference"]))
            target: str = path["l10n"]  # Note: not normalised, so sep=="/"
            if env_map:
                target = target.format_map(env_map)
            self._templates.append((path_stars.sub("{}", ref), path_regex(target)))
            locales: list[str] | None = path.get("locales", None)
            if "*" in ref:
                tail = ref[ref.index("*") :].replace(sep, "/")
                ref_base = ref[: -len(tail)]
                if target.endswith(tail):
                    target = target[: -len(tail)]
                elif "*" in target:
                    raise ValueError(
                        f"Wildcard mismatch between reference & l10n: {path}"
                    )
                self._path_data.update(
                    (ref_file, (ref_file.replace(ref_base, target, 1), locales))
                    for ref_file in glob(ref, recursive=True)
                    if isfile(ref_file)
                )
            else:
                self._path_data[ref] = (target, locales)

        self._includes: list[L10nConfigPaths] = []
        if "includes" in toml:
            if _seen is None:
                _seen = set()
            for incl in toml["includes"]:
                incl_path: str = incl["path"]
                if env_map:
                    incl_path = incl_path.format_map(env_map)
                incl_path = normpath(join(self._ref_root, incl_path))
                if incl_path not in _seen:
                    _seen.add(incl_path)
                    self._includes.append(
                        L10nConfigPaths(incl_path, cfg_load, _seen=_seen)
                    )

    @property
    def ref_root(self) -> str:
        """The reference root directory."""
        return self._ref_root

    @property
    def ref_paths(self) -> Iterator[str]:
        yield from self._path_data
        for incl in self._includes:
            yield from incl.ref_paths

    def config_paths(self) -> Iterator[str]:
        yield self._cfg_path
        for incl in self._includes:
            yield from incl.config_paths()

    def all(
        self, format_map: dict[str, str] | None = None
    ) -> dict[tuple[str, str], list[str] | None]:
        """
        Returns a mapping of `(reference_path, target_path)` to `locales`
        for all resources.

        In target paths, `{l10n_base}` is replaced by `self.base`.
        Any `{locale}` or `locale_map` variables will be left in.
        Additional format variables may be set in `format_map`.
        """
        all: dict[tuple[str, str], list[str] | None] = {}
        for key, locales in self._all(format_map):
            prev = all.get(key, None)
            if prev is None:
                all[key] = locales
            elif locales:
                locales_ = list(set(prev).union(locales))
                locales_.sort()
                all[key] = locales_
        return all

    def _all(
        self, format_map: dict[str, str] | None
    ) -> Iterator[tuple[tuple[str, str], list[str] | None]]:
        lc_map = PartialMap(format_map or ())
        lc_map["l10n_base"] = self.base
        for ref, (target, locales) in self._path_data.items():
            target = target.format_map(lc_map)
            if target.endswith(".pot"):
                target = target[:-1]
            target = normpath(join(self.base, target))
            yield (ref, target), locales or self.locales
        for incl in self._includes:
            yield from incl._all(format_map)

    def target_locales(self, ref_path: str) -> set[str]:
        """Returns the locales for which `ref_path` is translated."""
        norm_ref_path = normpath(join(self._ref_root, ref_path))
        if norm_ref_path.endswith(".po"):
            norm_ref_path += "t"
        pd = self._path_data.get(norm_ref_path, None)
        if pd:
            locales = set(pd[1] or self.locales or ())
        else:
            locales = set()
        for incl in self._includes:
            locales.update(incl.target_locales(ref_path))
        return locales

    def target_path(
        self,
        ref_path: str,
        locale: str | None = None,
        format_map: dict[str, str] | None = None,
    ) -> str | None:
        """
        If `ref_path` is a valid reference path,
        returns its corresponding target path.
        Otherwise, returns `None`.

        In the target path, `{l10n_base}` is replaced by `self.base`.
        If `locale` is not set,
        any `{locale}` or `locale_map` variables will be left in.
        Additional format variables may be set in `format_map`.
        """
        norm_ref_path = normpath(join(self._ref_root, ref_path))
        if norm_ref_path.endswith(".po"):
            norm_ref_path += "t"
        pd = self._path_data.get(norm_ref_path, None)
        if pd is None:
            for incl in self._includes:
                path = incl.target_path(ref_path, locale, format_map)
                if path is not None:
                    return path
            return None
        lc_map = PartialMap(format_map or ())
        lc_map["l10n_base"] = self.base
        if locale is not None:
            if pd[1] is not None and locale not in pd[1]:
                return None
            lc_map["locale"] = locale
            for key, fn in self._locale_map.items():
                lc_map[key] = fn(locale)
        target = pd[0].format_map(lc_map)
        if target.endswith(".pot"):
            target = target[:-1]
        return normpath(join(self.base, target))

    def format_target_path(self, target: str, locale: str) -> str:
        lc_map = {"locale": locale}
        for key, fn in self._locale_map.items():
            lc_map[key] = fn(locale)
        return normpath(join(self.base, target.format_map(lc_map)))

    def find_reference(self, target: str) -> tuple[str, dict[str, str]] | None:
        """
        A reverse lookup for the reference path and variables matching `target`,
        or `None` if not found.
        """
        target = relpath(join(self.base, normpath(target)), self.base)
        target = normpath(target).replace(sep, "/")
        for ref, pattern in self._templates:
            match = pattern.fullmatch(target)
            if match:
                vars = match.groupdict()
                star_values = match.groups()[len(vars) :]
                return normpath(ref.format(*star_values)), vars
        for incl in self._includes:
            res = incl.find_reference(target)
            if res is not None:
                return res
        return None
