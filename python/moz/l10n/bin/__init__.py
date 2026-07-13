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

import click
from moz.l10n.bin import build, build_file, compare, fix, lint, migrate


@click.group()
@click.version_option(package_name="moz-l10n")
def cli() -> None:
    """Welcome to the Mozilla Localization CLI Suite."""


cli.add_command(build.cli, name="build")
cli.add_command(build_file.cli, name="build-file")
cli.add_command(compare.cli, name="compare")
cli.add_command(lint.cli, name="lint")
cli.add_command(fix.cli, name="fix")
cli.add_command(migrate.cli, name="migrate")
