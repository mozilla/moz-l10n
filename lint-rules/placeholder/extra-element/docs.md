# `placeholder.extra-element`

## Description

The translation contains an additional markup element (e.g. `<b>`, `<br>`) that does not appear in the source string.

The diagnostic wording follows the style:
- `Element <x> not found in reference`

This is the mirror of [`placeholder.missing-element`](../missing-element/docs.md)

## Severity.ERROR

Extra markup can break layout or produce invalid output.

## How to fix?

Remove the element that has no counterpart in the source, or if it
is genuinely needed, request a fix in the source.

## Example

Reference:
```
Source string
```
Translation:
```
Translation <br> with a linebreak
```
> 🚫 `Element <br> not found in reference`
