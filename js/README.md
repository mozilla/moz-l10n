# @mozilla/l10n

This is a library of JavaScript tools and utilities for working with localization files,
primarily built for internal use at Mozilla.

It's being bootstrapped to fulfil the needs of the [Pontoon](https://pontoon.mozilla.org/) frontend,
and to match the behaviour of the Python [moz.l10n](https://pypi.org/project/moz.l10n/) library.

The data structures used by the library are defined by a
[JSON Schema](https://github.com/mozilla/moz-l10n/blob/main/schemas/message.json).

The library currently supports the following message pattern formats:

- `android`: Android string resources
- `fluent`: Fluent (without internal selectors)
- `mf2`: MessageFormat 2.0
- `plain`: Patterns without placeholders (used in multiple resource formats)
- `webext`: WebExtensions (messages.json)
- `xliff`: XLIFF 1.2, including XCode customizations

The tooling for `android` and `xliff` depends on `DOMParser`, `XMLSerializer`, and related classes
which are available in browser environments.
The parser for `fluent` depends on the `@fluent/syntax` package,
and the parser for `mf2` depends on the `messageformat` package.

## API

### parsePattern()

```js
import { ParseError, parsePattern } from '@mozilla/l10n'
```

```js
function parsePattern(
  format: 'android' | 'fluent' | 'mf2' | 'plain' | 'webext' | 'xliff',
  src: string,
  baseMsg?: Message
): Pattern

class ParseError extends Error {
  range?: [number, number]  // Set for fluent, mf2, and webext errors
}
```

Parse the string representation of a single flat message pattern into a data structure
([JSON Schema](https://github.com/mozilla/moz-l10n/blob/main/schemas/message.json)).

The `baseMsg` is required by `webext` for named placeholders.

If `onError` is undefined, errors are thrown.

### serializePattern()

```js
import { SerializeError, serializePattern } from '@mozilla/l10n'
```

```js
function serializePattern(
  format: 'android' | 'fluent' | 'mf2' | 'plain' | 'webext' | 'xliff',
  pattern: Pattern,
  onError?: (error: SerializeError) => void
): string

class SerializeError extends Error {
  pos?: number  // Set for fluent, plain, and webext errors
}
```

Serialize the data representation of a single flat message pattern into a string

If `onError` is undefined, errors are thrown.

### Types

```ts
import type {
  Message,
  PatternMessage,
  SelectMessage,
  Pattern,
  Expression,
  Markup
} from '@mozilla/l10n'
```

```ts
type Message = Pattern | PatternMessage | SelectMessage
type Pattern = (string | Expression | Markup)[]
```
