# `message-id-mismatch`

## Description

A Fluent translation is a full entry — `id = value` — so the translator can, by
accident, change the message identifier. The id in the translation must be
identical to the id of the source message it translates.

## Why is this bad?

The id is the key the product uses to look the string up. If the translation's
id drifts from the source id, the localized string is silently dropped (the
product falls back to the source, or fails the lookup) even though the
translation looks complete.

## Example

```ftl
# source.ftl
key = value

# example.ftl — id was changed to key1
key1 = translation
```

## How to fix?

Restore the original identifier and translate only the value/attributes:

```ftl
key = translation
```
