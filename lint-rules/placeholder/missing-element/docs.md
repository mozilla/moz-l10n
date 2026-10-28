# `placeholder.missing-element`

## Description

A markup element present in the source string does not appear in the translation.

The diagnostic wording follows the style:
- `Element <x> not found in translation`

This is the mirror of [`placeholder.extra-element`](../extra-element/docs.md)

## Severity.WARNING

This is reported as a **warning** because a translator may legitimately drop an element in some grammatical constructions.

## How to fix?

Reintroduce the missing placeholder/element where it belongs in the translation.
If it is intentionally omitted, the warning can be acknowledged.

## Example

Reference:
```
Source string with a <a href="https:some.where">link!</a>
```
Translation:
```
Translation without a link!
```
> ⚠️ `Element <x> not found in translation`
