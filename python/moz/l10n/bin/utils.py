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

import logging

import click

LOG_FORMAT: str = "%(message)s"


def make_list_option_class(
    option_names: str | list[str] | tuple[str] | None = None,
    custom_usage: str | None = None,
) -> type[click.Command]:
    """
    Generate unique click.Command class to:

    * support argparse-style multi-token `nargs="+"` flags. e.g.:
      `--locales fr de --coverage ...`
    * have custom "Usage: " declaration on `--help`
    """
    normalized_options = set()
    if option_names:
        normalized_options.update(
            {option_names} if isinstance(option_names, str) else option_names
        )

    class CustomMultiCommand(click.Command):
        def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
            if not normalized_options:
                return super().parse_args(ctx, args)

            new_args = []
            i = 0
            while i < len(args):
                this_arg = args[i]
                new_args.append(this_arg)
                if this_arg not in normalized_options:
                    i += 1
                    continue

                i += 1
                first = True
                # Consume all upcoming items until end or another dash flag
                while i < len(args) and not args[i].startswith("-"):
                    if not first:
                        # Inject flag name again to satisfy Click's multiple=True
                        new_args.append(this_arg)
                    new_args.append(args[i])
                    first = False
                    i += 1
            return super().parse_args(ctx, new_args)

        def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter):
            if custom_usage:
                formatter.write_usage(ctx.command_path, custom_usage)
            else:
                super().format_usage(ctx, formatter)

    return CustomMultiCommand


def cli_settify(
    context: click.Context, param: click.Parameter, value: tuple[str, ...]
) -> set[str]:
    """Help turning incoming `tuple` value to `set` via click-decorator.
    So we don't have to deal with that in the code.
    """
    if not value:
        return set()
    items = []
    for item in value:
        items.append(item.strip(", \t"))
    return set(items)


def set_log_level(verbose: int, quiet: bool = False) -> int:
    """Deal with `verbose` integer initializing `logging` with the according level.
    * 0 -> logging.WARNING. Default. Only warnings and errors are logged.
    * 1 -> logging.INFO. Info messages are logged as well.
    * 2 -> logging.DEBUG. Moste verbose. Also debug messages are logged.

    Also returns the logging built-in level integer (10, 20, 30).
    """
    log_level = (
        logging.ERROR
        if quiet
        else (
            logging.WARNING
            if not verbose
            else logging.INFO
            if verbose == 1
            else logging.DEBUG
        )
    )
    logging.basicConfig(format=LOG_FORMAT, level=log_level)
    return log_level
