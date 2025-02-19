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
- `inc`: .inc
- `ini`: .ini
- `plain_json`: Plain JSON (.json)
- `po`: Gettext (.po, .pot)
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

Uses the `--source` file as a baseline, applying `--l10n` localizations to build `--target`.
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

### moz.l10n.message: from_json() and to_json()

```python
from moz.l10n.message import from_json, to_json

def message_from_json(json: list[Any] | dict[str, Any]) -> Message: ...
def message_to_json(msg: Message) -> list[Any] | dict[str, Any]: ...
```

Converters to and from a JSON-serializable representation of a `Message`.
The format of the output is defined by the [`schema.json`](./moz/l10n/message/schema.json) JSON Schema.

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
as the file will be opened and read.

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
