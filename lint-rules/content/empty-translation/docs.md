# `empty-translation`

## Description

The source does contain content but not the translation. This covers a genuinely empty
string as well as messages whose pattern resolves to nothing — for example a
Fluent value of `{ "" }`, an MF2 message of `{{}}`, or a plural message all of
whose variants are empty.
Note: Whitespace such as ` ` or `\n` is NOT considered empty!

## Why is this bad?

An empty translation ships a blank string to users where text is expected. For
most formats this is an **error** and blocks submission. Some resources
legitimately allow empty values (Pontoon's `allows_empty_translations`); for
those the rule downgrades to a **warning** via the `allowed_severity` option so
the emptiness is still recorded but not blocking.

Note the interaction with plurals: an empty *and* pluralized translation over a
non-plural source raises both this rule and
[`plural-source-required`](../../structure/plural-source-required/docs.md).

## Example

```ftl
# example.ftl — value resolves to empty string
key = { "" }
```

## How to fix?

Provide real translated content, e.g. `key = { "translated" }`. If the string
is intentionally blank, ensure the resource is configured to allow empty
translations.
