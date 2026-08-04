# `invalid-localizable-entry`

## Description

The translation parses as valid Fluent but is not a localizable entry — i.e. it
is not a `Message` or a `Term`. Comments, standalone junk, or other non-message
entries are not acceptable as the translation of a message.

This is distinct from [`parse-error`](../../syntax/parse-error/docs.md): the
input is syntactically valid Fluent, it is just the wrong *kind* of entry.

## Why is this bad?

Pontoon stores one translation per source message. If the submitted entry is
not a message/term, there is no value to store against the source id and the
translation is meaningless.

## Example

```ftl
# example.ftl — not a message or term
[[foo]]
```

## How to fix?

Submit a proper message whose id matches the source, e.g. `key = translation`.
