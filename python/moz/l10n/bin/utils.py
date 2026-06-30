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
    option_names: str | list[str] | tuple[str],
) -> type[click.Command]:
    """
    Generate unique click.Command class to support argparse-style multi-token `nargs="+"` flags.
    e.g.:
        --locales fr de --coverage
    """
    normalized_options = (
        {option_names} if isinstance(option_names, str) else set(option_names)
    )

    class CustomMultiCommand(click.Command):
        def parse_args(self, ctx, args):
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
        items.append(item.strip(', \t'))
    return set(items)


def set_log_level(verbose: int) -> int:
    log_level = (
        logging.WARNING
        if not verbose
        else logging.INFO
        if verbose == 1
        else logging.DEBUG
    )
    logging.basicConfig(format=LOG_FORMAT, level=log_level)
    return log_level
