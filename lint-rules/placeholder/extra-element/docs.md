# `placeholder.extra-element`

## Description

The translation contains a markup element (e.g. `<b>`, `<br>`) that does not appear in the source string.

The diagnostic wording follows the item kind:

- `Element <x> not found in reference`

## Why is this bad?

Extra markup can break layout or produce invalid output.

## Example

```
# source.xml — no placeholder
Source string

# example.xml — translation invents a %1$s
Translation with a %1$s
```

## How to fix?

Remove the element that has no counterpart in the source, or if it
is genuinely needed, care for correction of the source so it declares it.