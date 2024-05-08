# moz.l10n

This is a library of Python tools and utilities for working with localization files,
primarily built for internal use at Mozilla.

The core idea here is to establish [Message](./moz/l10n/message.py) and [Resource](./moz/l10n/resource.py)
as format-independent representations of localizable and localized messages and resources,
so that operations like linting and [transforms](./moz/l10n/transform/) can be applied to them.

Parsers and serializers are provided for a number of formats,
using common and well-established libraries to take care of the details.
A unified API for these is provided,
such that `FORMAT_parse(text)` will always accept `str` input,
and `FORMAT_serialize(resource)` will always provide a `str` iterator.
All the serializers accept a `trim_comments` argument
which leaves out comments from the serialized result,
but additional input types and options vary by format.

The Message and Resource representations are drawn from work done for the
Unicode [MessageFormat 2 specification](https://github.com/unicode-org/message-format-wg/tree/main/spec)
and the [Message resource specification](https://github.com/eemeli/message-resource-wg/).

## moz.l10n.resources

### detect_format

```python
def detect_format(name: str | None, source: bytes | str) -> Format | None
```

Detect the format of the input based on its file extension
and/or contents.

Returns a `Format` enum value, or `None` if the input is not recognized.

### iter_resources

```python
def iter_resources(
    root: str,
    dirs: list[str] | None = None,
    ignorepath: str = ".l10n-ignore"
) -> Iterator[tuple[str, Resource[Message, str] | None]]
```

Iterate through localizable resources under the `root` directory.
Use `dirs` to limit the search to only some subdirectories under `root`.

Yields `(str, Resource | None)` tuples,
with the file path and the corresponding `Resource`,
or `None` for files that could not be parsed as localization resources.

To ignore files, include a `.l10n-ignore` file in `root`,
or some other location passed in as `ignorepath`.
This file uses a git-ignore syntax,
and is always based in the `root` directory.

### parse_resource

```python
def parse_resource(
    type: Format | str | None,
    source: str | bytes
) -> Resource[Message, str]
```

Parse a Resource from its string representation.

The first argument may be an explicit Format,
the filename as a string, or None.
For the latter two types,
an attempt is made to detect the appropriate format.

### serialize_resource

```python
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
