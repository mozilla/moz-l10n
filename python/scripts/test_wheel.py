#!/usr/bin/env python3
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

# /// script
# requires-python = ">=3.9"
# dependencies = ["click ~= 8.1"]
# ///

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import click

ROOT = Path(__file__).parent.parent.parent
BIN_DIR = "Scripts" if sys.platform == "win32" else "bin"
EXE = ".exe" if sys.platform == "win32" else ""


def run(*args: str | Path, cwd: Path | None = None) -> None:
    """Compact `subprocess.run` with `check=True` and logging."""
    cmd_list = [str(arg) for arg in args]
    click.echo(f"\nRunning: {' '.join(cmd_list)}")
    subprocess.run(cmd_list, cwd=cwd, check=True)


def check_wheel(wheel: Path | None, dist: Path) -> Path:
    """Pass wheel location if existing, build in place if not and pass path."""
    if wheel is not None and wheel.is_file():
        return wheel.resolve()

    run("uv", "build", "--project", ROOT / "python", "--wheel", "-o", dist)
    wheels = list(dist.glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected exactly ONE wheel in {dist}, found {len(wheels)}")
    return wheels[0]


def stage_tests(dest: Path) -> Path:
    """Copy tests and data to temp destination."""
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
    shutil.copytree(ROOT / "python" / "tests", dest / "python" / "tests", ignore=ignore)
    shutil.copytree(ROOT / "schemas", dest / "schemas", ignore=ignore)
    return dest / "python"


@click.command(help=__doc__)
@click.option(
    "-p",
    "--python",
    "python_version",
    metavar="VERSION",
    help="Python version to test with. Default: From calling runtime.",
)
@click.option(
    "-w",
    "--wheel",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Wheel to test, Default: building one in place.",
)
def cli(python_version: str | None, wheel: Path | None) -> None:
    """
    Run our Python test suite against a built moz.l10n wheel.

    Tests are copied out of the repository before run.
    `pytest` would otherwise put `python/` on sys.path via `pythonpath` setting.
    And since `tests` is a package `moz` source directory would shadow the installed wheel.

    Keeps `./python/tests` and `./schemas` layout some tests rely on to find data.

    \b
    Usage:
        uv run python/scripts/test_wheel.py [--python 3.12] [--wheel path/to.whl]
    """
    if python_version is None:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    with TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        wheel = wheel.resolve() if wheel else check_wheel(wheel, tmp_dir / "dist")
        cwd = stage_tests(tmp_dir / "repo")

        venv = tmp_dir / "venv"
        python_path = venv / BIN_DIR / f"python{EXE}"
        run("uv", "venv", "--python", python_version, venv)

        pip_install = ("uv", "pip", "install", "--python", python_path)
        run(*pip_install, wheel, "pytest", "jsonschema", "pytest-subtests")
        run(python_path, "-m", "pytest", "-vv", cwd=cwd)
        run(venv / BIN_DIR / f"moz-l10n{EXE}", "--help")

        # Test again with XML support installed
        run(*pip_install, f"{wheel}[xml]")
        run(python_path, "-m", "pytest", "-vv", cwd=cwd)

    click.echo("\nThe built package passes its test suite.")


if __name__ == "__main__":
    cli()
