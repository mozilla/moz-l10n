# `placeholder.not-in-reference`

## Description

The translation contains a placeholder (e.g. `%1$s`, `%@`, `$FOO$`) or a markup
element (e.g. `<b>`, `<br>`) that does not appear in the source string. This
holds whether the item is written as a real placeholder/expression or as
literal text in the translation.

The diagnostic wording follows the item kind:

- `Placeholder <x> not found in reference` for printf-style placeholders
- `Element <x> not found in reference` for HTML/XML markup

## Why is this bad?

Placeholders are substituted at runtime with values the source declares. A
placeholder that the source does not provide will be rendered literally or, for
some formatters, crash the format call. Extra markup can likewise break layout
or produce invalid output.

## Example

```
# source.xml — no placeholder
Source string

# example.xml — translation invents a %1$s
Translation with a %1$s
```

## How to fix?

Remove the placeholder/element that has no counterpart in the source, or — if it
is genuinely needed — correct the source so it declares it.
