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

from os import sep, walk
from os.path import commonpath, isdir, join, normpath, relpath, splitext
from re import compile

from moz.l10n.resource.format import l10n_extensions
from moz.l10n.util import walk_files

REF_DIR_SCORES = {
    "templates": 3,
    "en-US": 2,
    "en-us": 2,
    "en_US": 2,
    "en_us": 2,
    "en": 1,
}

locale_id = compile(
    r"[a-z]{2}(?:[-_][A-Z][a-z]{3})?(?:[-_][A-Z]{2})?|ca-valencia|ja-JP-mac"
)


def dir_contains(dir: str, path: str) -> bool:
    return commonpath((dir, path)) == dir


def locale_dirname(base: str, locale: str) -> str:
    if "-" in locale and not isdir(join(base, locale)):
        alt_dir = locale.replace("-", "_")
        if isdir(join(base, alt_dir)):
            return alt_dir
    return locale


class MissingSourceDirectoryError(Exception):
    """Raised when no source directory can be found."""


class L10nDiscoverPaths:
    """
    Automagical localization resource discovery.

    Given a root directory, finds the likeliest reference and target directories.

    The reference directory has a name like `templates`, `en-US`, or `en`,
    and contains files with extensions that appear localizable.

    The localization target root is a directory with subdirectories named as
    BCP 47 locale identifiers, i.e. like `aa`, `aa-AA`, `aa-Aaaa`, or `aa-Aaaa-AA`.

    An underscore may also be used as a separator, as in `en_US`.
    """

    base: str | None
    """The target base directory, with subdirectories for each locale."""
    locales: list[str] | None
    """Locales detected from subdirectory names under `base`."""
    ref_paths: tuple[str, ...]
    """Reference paths"""

    def __init__(
        self,
        root: str,
        ref_root: str | None = None,
        ignorepath: str | None = ".l10n-ignore",
    ) -> None:
        """
        To ignore files, include a `.l10n-ignore` file in the reference base directory
        or some other location passed in as `ignorepath`.
        This file uses git-ignore syntax,
        and is always based in the reference base directory.
        """
        root = normpath(root)
        if not isdir(root):
            raise ValueError(f"Not a directory: {root}")
        if ref_root:
            ref_root = normpath(join(root, ref_root))

        ref_dirs: dict[str, int] = {}  # dir -> score
        base_dirs: list[tuple[str, list[str]]] = []  # [(root, [locale_dir])]
        pot_dirs: list[str] = []
        l10n_dirs: list[str] = []
        for dirpath, dirnames, filenames in walk(root):
            locale_dirs = []
            for dir in dirnames:
                if dir in REF_DIR_SCORES:
                    if not ref_root:
                        ref_dirs[join(dirpath, dir)] = REF_DIR_SCORES[dir]
                elif locale_id.fullmatch(dir):
                    locale_dirs.append(dir)
            if locale_dirs:
                base_dirs.append((dirpath, locale_dirs))
            dirnames[:] = (dn for dn in dirnames if not dn.startswith("."))

            if any(not fn.startswith(".") and fn.endswith(".pot") for fn in filenames):
                pot_dirs.append(dirpath)
            if any(
                not fn.startswith(".") and splitext(fn)[1] in l10n_extensions
                for fn in filenames
            ):
                l10n_dirs.append(dirpath)

        if ref_root:
            self._ref_root = ref_root
        else:
            # Filter reference dirs to those with localizable contents,
            # with a preference for .pot template files.
            ref_dirs_with_files = [
                dir for dir in ref_dirs if any(dir_contains(dir, pd) for pd in pot_dirs)
            ] or [
                dir
                for dir in ref_dirs
                if any(dir_contains(dir, ld) for ld in l10n_dirs)
            ]
            if ref_dirs_with_files:
                self._ref_root = max(
                    (rd for rd in ref_dirs.items() if rd[0] in ref_dirs_with_files),
                    key=lambda s: s[1],
                )[0]
            else:
                raise MissingSourceDirectoryError

        if dir_contains(self._ref_root, root):
            self.base = None
            self.locales = None
        else:
            # Pick the localization base dir not in the reference directory
            # with the most locale subdirectories,
            # with a preference for directories with localizable contents.
            base_dirs = [
                bd for bd in base_dirs if not dir_contains(self._ref_root, bd[0])
            ]
            base_dirs = [
                bd
                for bd in base_dirs
                if any(dir_contains(bd[0], ld) for ld in l10n_dirs)
            ] or base_dirs

            locale_dirs_: list[str] | None
            self.base, locale_dirs_ = max(
                base_dirs, key=lambda s: len(s[1]), default=(None, None)
            )
            if locale_dirs_:
                self.locales = [dir.replace("_", "-") for dir in locale_dirs_]
                self.locales.sort()
            else:
                self.locales = None

        self.ref_paths = (
            tuple(walk_files(self._ref_root, ignorepath=ignorepath))
            if isdir(self._ref_root)
            else ()
        )

    @property
    def ref_root(self) -> str:
        """The reference root directory."""
        return self._ref_root

    def _base(self) -> str:
        if self.base is None:
            raise ValueError("self.base is required for target paths")
        return self.base

    def all(self) -> dict[tuple[str, str], list[str] | None]:
        """
        Returns a mapping of `(reference_path, target_path)` to `locales`
        for all resources.

        Target paths will include a `{locale}` variable.
        """
        locale_root = join(self._base(), "{locale}")
        paths: dict[tuple[str, str], list[str] | None] = {}
        for ref_path in self.ref_paths:
            target = ref_path.replace(self._ref_root, locale_root, 1)
            if target.endswith(".pot"):
                target = target[:-1]
            paths[(ref_path, target)] = self.locales
        return paths

    def target_locales(self, _ref_path: str = "") -> set[str]:
        return set(self.locales or ())

    def target_path(self, ref_path: str, locale: str | None = None) -> str | None:
        """
        If `ref_path` is a valid reference path,
        returns its corresponding target path.
        Otherwise, returns `None`.

        If `locale` is not set,
        target path will include a `{locale}` variable.
        """
        ref_path = normpath(join(self._ref_root, ref_path))
        if ref_path.endswith(".po"):
            ref_path += "t"
        if ref_path not in self.ref_paths:
            return None
        locale_root = join(self._base(), "{locale}" if locale is None else locale)
        target = ref_path.replace(self._ref_root, locale_root, 1)
        return target[:-1] if target.endswith(".pot") else target

    def format_target_path(self, target: str, locale: str) -> str:
        base = self._base()
        dir = locale_dirname(base, locale)
        return normpath(join(base, target.format(locale=dir)))

    def find_reference(self, target: str) -> tuple[str, dict[str, str]] | None:
        """
        A reverse lookup for the reference path and locale matching `target`,
        or `None` if not found.

        The locale is returned as `{"locale": locale}` to match `L10nConfig`.
        """
        base = self._base()
        locale, *path_parts = normpath(relpath(join(base, target), base)).split(sep)
        return (
            (join(self._ref_root, *path_parts), {"locale": locale.replace("_", "-")})
            if path_parts and locale_id.fullmatch(locale)
            else None
        )
