# `placeholder.extra`

## Description

The translation contains an additional placeholder (e.g. `%1$s`, `%@`, `$FOO$`) that does not appear in the source string.

The diagnostic wording follows the item kind:
- `Placeholder <x> not found in reference`

## Why is this bad?

Placeholders are substituted at runtime with values the source declares. A
placeholder that the source does not provide will be rendered literally or, for
some formatters, crash the format call.

## Example

```
# source.xml — no placeholder
Source string

# example.xml — translation invents a %1$s
Translation with a %1$s
```

## How to fix?

Remove the placeholder/element that has no counterpart in the source, or if it
is genuinely needed, care for correction of the source so it declares it.