# moz.l10n

This is a library of Python tools and utilities for working with localization files,
primarily built for internal use at Mozilla.

The core idea here is to establish [Message](./moz/l10n/message.py) and [Resource](./moz/l10n/resource.py)
as format-independent representations of localizable and localized messages and resources,
so that operations like linting and transforms can be applied to them.

The Message and Resource representations are drawn from work done for the
Unicode [MessageFormat 2 specification](https://unicode.org/reports/tr35/tr35-messageFormat.html)
and the [Message resource specification](https://github.com/eemeli/message-resource-wg/).

The library currently supports the following resource formats:

- `android`†: Android string resources (strings.xml)
- `dtd`: .dtd
- `fluent`: Fluent (.ftl)
- `gettext`: Gettext (.po, .pot)
- `inc`: .inc
- `ini`: .ini
- `plain_json`: Plain JSON (.json)
- `properties`: .properties
- `webext`: WebExtensions (messages.json)
- `xliff`†: XLIFF 1.2, including XCode customizations (.xlf, .xliff)

**†** Support for XML formats (`android`, `xliff`) is an optional extra;
to support them, install as `moz.l10n[xml]`.

## Command-line Tools

For usage details, use each command's `--help` argument.

### `l10n-build`

Build localization files for release.

Iterates source files as defined by `--config`, reads localization sources from `--base`, and writes to `--target`.
Trims out all comments and messages not in the source files for each of the `--locales`.
Adds empty files for any missing from the target locale.

### `l10n-build-file`

Build one localization file for release.

Uses the `--source` file as a baseline, applying `--l10n` localizations (if set) to build `--target`.
Trims out all comments and messages not in the source file.

### `l10n-compare`

Compare localizations to their `source`, which may be

- a directory (using `L10nDiscoverPaths`),
- a TOML config file (using `L10nConfigPaths`), or
- a JSON file containing a mapping of file paths to arrays of messages.

### `l10n-fix`

Fix the formatting for localization resources.

If `paths` is a single directory, it is iterated with `L10nConfigPaths` if `--config` is set, or `L10nDiscoverPaths` otherwise.
If `paths` is not a single directory, its values are treated as glob expressions, with `**` support.

## Python API

### moz.l10n.formats.FORMAT

Parsers and serializers are provided for a number of formats,
using common and well-established libraries to take care of the details.
A unified API for these is provided,
such that `FORMAT_parse(text)` will always accept `str` input,
and `FORMAT_serialize(resource)` will always provide a `str` iterator.
All the serializers accept a `trim_comments` argument
which leaves out comments from the serialized result,
but additional input types and options vary by format.

### moz.l10n.formats.mf2

```python
from moz.l10n.formats.mf2 import (
    MF2ParseError,          # May be raised by mf2_parse_message()
    MF2ValidationError,     # May be raised by mf2_from_json() and mf2_validate_message()
    mf2_parse_message,      # Parse MF2 message syntax into a Message
    mf2_serialize_message,  # Serialize a Message using MF2 syntax
    mf2_from_json,          # Marshal a MF2 data model JSON Schema object into a Message
    mf2_to_json,            # Represent a Message using the MF2 data model JSON Schema
    mf2_validate_message    # Validate that a Message meets all of the MF2 validity constraints
)
```

Tools for working with [MessageFormat 2.0](https://unicode.org/reports/tr35/tr35-messageFormat.html) messages,
which may be embedded in resource formats.

### moz.l10n.formats.detect_format

```python
from moz.l10n.formats import detect_format

def detect_format(name: str | None, source: bytes | str) -> Format | None
```

Detect the format of the input based on its file extension
and/or contents.

Returns a `Format` enum value, or `None` if the input is not recognized.

### moz.l10n.message: entry_from_json() and entry_to_json()

```python
from moz.l10n.message import entry_from_json, entry_to_json

def entry_from_json(key: str, json: dict[str, Any]) -> Entry[Message]
def entry_to_json(entry: Entry[Message]) -> tuple[str, dict[str, Any]]
```

Converters to and from a JSON-serializable representation of an `Entry`.
The format of the output is defined by the [`entry.json`](../schemas/entry.json) JSON Schema.
Note that the stringified message identifier is handled separately from the other fields,
as it's meant to be used as a mapping key.

### moz.l10n.message: message_from_json() and message_to_json()

```python
from moz.l10n.message import message_from_json, message_to_json

def message_from_json(json: list[Any] | dict[str, Any]) -> Message
def message_to_json(msg: Message) -> list[Any] | dict[str, Any]
```

Converters to and from a JSON-serializable representation of a `Message`.
The format of the output is defined by the [`message.json`](../schemas/message.json) JSON Schema.

### moz.l10n.message.parse_message

```python
from moz.l10n.message import parse_message

def parse_message(
    format: Format,
    source: str,
    *,
    printf_placeholders: bool = False,
    webext_placeholders: dict[str, dict[str, str]] | None = None,
    xliff_is_xcode: bool = False,
) -> Message
```

Parse a `Message` from its string representation.

Custom parsers are used for `android`, `mf2`, `webext`, and `xliff` formats.
Other formats may include printf specifiers if `printf_placeholders` is enabled.

Parsing a `webext` message that contains named placeholders requires
providing the message's `webext_placeholders` dict.

To parse an `xliff` message with XCode customizations, enable `xliff_is_xcode`.

Parsing `fluent` messages is not supported,
as their parsing may result in multiple `Entry` values.

### moz.l10n.message.serialize_message

```python
from moz.l10n.message import serialize_message

def serialize_message(format: Format, msg: Message) -> str
```

Serialize a `Message` to its string representation.

Custom serialisers are used for `android`, `mf2`, `webext`, and `xliff` formats.
Many formats rely on non-string message parts including an appropriate `source` attribute.

SelectMessage serialization is only supported for `mf2`.

Serializing `fluent` messages is not supported.

### moz.l10n.migrate.apply_migration

```python
from moz.l10n.migrate import apply_migration

def apply_migration(
    res: Resource[Message] | str,
    changes: dict[
        tuple[str, ...] | str,
        Callable[
            [Resource[Message], Ctx | None],
            Message
            | Entry[Message]
            | Tuple[Message | Entry[Message], tuple[tuple[str, ...] | str, ...] | str],
        ],
    ],
    context: Ctx | None = None,
) -> int
```

Applies `changes` to a Resource `res`.

If `res` is a string, the resource at that path is parsed is modified.

The `changes` are a mapping of target entry identifiers to functions that define their values;
the function will be called with two arguments `(res: Resource, context: Ctx)`,
passing through the unmodified `context` given to this function (`None` by default).

Change functions should return a Message, an Entry, or a tuple consisting of one of those,
along with one or more identifiers for entries after which the new entry should be inserted.

If an entry already exists with the target identifier,
it is not modified.

### moz.l10n.migrate.copy

```python
from moz.l10n.migrate import copy

def copy(
    ref_path: None | str,
    id: tuple[str, ...] | str,
    variant: tuple[str | CatchallKey, ...] | str | None = None,
) -> Callable[
    [Resource[Message], MigrationContext],
    tuple[Entry[Message] | Message, set[tuple[str, ...]]] | None,
]
```

Create a copy migration function, from entry `id` in `ref_path`.

If `ref_path` is None, the entry is copied from the current Resource.

If `variant` is set and `id` contains a SelectMessage,
the pattern of the specified variant is copied (or the default one).

### moz.l10n.migrate.utils

```python
from moz.l10n.migrate.utils import (
    MigrationContext,
    get_entry,
    get_pattern,
    plural_message,
)

def make_plural_x(res, ctx: MigrationContext):
    x_other = get_pattern(res, "x-other")
    x_one = get_pattern(res, "x-one", default=x_other)
    x_two = get_pattern(res, "x-two", default=x_other)
    msg = plural_message("quantity", one=x_one, two=x_two, other=x_other)
    return msg, {"x-one", "x-two", "x-other"}
```

Utilities for putting together more complex message migrations.
See individual [doc comments](moz/l10n/migrate/utils.py) for more information,
and [test suite](tests/test_migrate.py) for example usage.

### moz.l10n.model

```python
from moz.l10n.model import (
    # Resource dataclasses
    Resource,
    Section,
    Entry,
    Comment,
    Metadata,
    LinePos,  # The source line position of an entry or section header.

    # Message dataclasses
    Message,  # type alias for PatternMessage | SelectMessage
    PatternMessage,
    SelectMessage,
    CatchallKey,
    Pattern,  # type alias for list[str | Expression | Markup]
    Expression,
    Markup,
    VariableRef
)
```

Dataclasses defining the library's representation of a messages and resources,
with messages either as a single-pattern `PatternMessage`,
or as a `SelectMessage` with one or more selectors and multiple variant patterns.

### moz.l10n.paths.L10nConfigPaths

Wrapper for localization config files.

Supports a subset of the format specified at:
https://moz-l10n-config.readthedocs.io/en/latest/fileformat.html

Differences:

- `[build]` is ignored
- `[[excludes]]` are not supported
- `[[filters]]` are ignored
- `[[paths]]` must always include both `reference` and `l10n`

Does not consider `.l10n-ignore` files.

### moz.l10n.paths.L10nDiscoverPaths

Automagical localization resource discovery.

Given a root directory, finds the likeliest reference and target directories.

The reference directory has a name like `templates`, `en-US`, or `en`,
and contains files with extensions that appear localizable.

The localization target root is a directory with subdirectories named as
BCP 47 locale identifiers, i.e. like `aa`, `aa-AA`, `aa-Aaaa`, or `aa-Aaaa-AA`.

An underscore may also be used as a separator, as in `en_US`.

### moz.l10n.resource.add_entries

```python
from moz.l10n.resource import add_entries

def add_entries(
    target: Resource,
    source: Resource,
    *,
    use_source_entries: bool = False
) -> int
```

Modifies `target` by adding entries from `source` that are not already present in `target`.
Standalone comments are not added.

If `use_source_entries` is set,
entries from `source` override those in `target` when they differ,
as well as updating section comments and metadata from `source`.

Entries are not copied, so further changes will be reflected in both resources.

Returns a count of added or changed entries and sections.

### moz.l10n.resource.l10n_equal

```python
from moz.l10n.resource import l10n_equal

def l10n_equal(a: Resource, b: Resource) -> bool
```

Compares the localization-relevant content
(id, comment, metadata, message values) of two resources.

Sections with no message entries are ignored,
and the order of sections, entries, and metadata is ignored.

### moz.l10n.resource.parse_resource

```python
from moz.l10n.resource import parse_resource

def parse_resource(
    input: Format | str | None,
    source: str | bytes | None = None
) -> Resource[Message, str]
```

Parse a Resource from its string representation.

The first argument may be an explicit Format,
the file path as a string, or None.
For the latter two types,
an attempt is made to detect the appropriate format.

If the first argument is a string path,
the `source` argument is optional,
as the file will be opened and read if `source` is not set.

### moz.l10n.resource.serialize_resource

```python
from moz.l10n.resource import serialize_resource

def serialize_resource(
    resource: Resource[str, str] | Resource[Message, str],
    format: Format | None = None,
    trim_comments: bool = False
) -> Iterator[str]
```

Serialize a Resource as its string representation.

If `format` is set, it overrides the `resource.format` value.

With `trim_comments`,
all standalone and attached comments are left out of the serialization.

### moz.l10n.util.walk_files

```python
from moz.l10n.util import walk_files

def walk_files(
    root: str,
    dirs: list[str] | None = None,
    ignorepath: str | None = ".l10n-ignore"
) -> Iterator[str]
```

Iterate through all files under the `root` directory.
Use `dirs` to limit the search to only some subdirectories under `root`.

All files and directories with names starting with `.` are ignored.
To ignore other files, include a `.l10n-ignore` file in `root`,
or some other location passed in as `ignorepath`.
This file uses git-ignore syntax,
and is always based in the `root` directory.
