# `placeholder.missing`

## Description

A placeholder present in the source string does not appear in the translation.
This is the mirror of [`placeholder-extra`](../extra/docs.md) and is
reported as a **warning** because a translator may legitimately drop a
placeholder in some grammatical constructions.

The diagnostic wording follows the item kind:

- `Placeholder <x> not found in translation`

## Why is this bad?

A dropped placeholder usually means the translation loses a dynamic value the
source intended to show (a count, a name, a link). It is often a mistake, but
because it is occasionally intentional it warns rather than blocks.

## Example

```
# source.xml — source provides a %1$s
Source string with a %1$s

# example.xml — translation omits it
Translation
```

## How to fix?

Reintroduce the missing placeholder where it belongs in the translation.
If it is intentionally omitted, the warning can be acknowledged.