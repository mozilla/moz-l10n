# moz.l10n

This is a library of Python tools and utilities for working with localization files,
primarily built for internal use at Mozilla.

The core idea here is to establish [Message](./moz/l10n/message.py) and [Resource](./moz/l10n/resource.py)
as format-independent representations of localizable and localized messages and resources,
so that operations like linting and [transforms](./moz/l10n/transform/) can be applied to them.

Parsers and serializers are provided for a number of formats,
using common and well-established libraries to take care of the details.
A unified API for these is provided,
such that `FORMAT_parse(source)` will always accept `str` input,
and `FORMAT_serialize(resource)` will always provide a `str` iterator.
All the serializers accept a `trim_comments` argument,
but additional input types and options vary by format.

The Message and Resource representations are drawn from work done for the
Unicode [MessageFormat 2 specification](https://github.com/unicode-org/message-format-wg/tree/main/spec)
and the [Message resource specification](https://github.com/eemeli/message-resource-wg/).
