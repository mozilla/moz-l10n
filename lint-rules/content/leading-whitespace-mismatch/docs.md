# `content.leading-whitespace-mismatch`

## Description

Source and translation should **both** start with the same whitespace or **neither** of them should have any leading whitespace.

## Why is this bad?

Leading whitespace may be significant in rendering localization output.
Adding or dropping it in the translation changes the rendered string relative to the source, which can
break formatting, concatenation, or byte-for-byte expectations in consuming code.

## Example

```
# source.po — no leading whitespace
Original
```

```
# example.po — translation adds a newline

Translation
```

## How to fix?

Make the translation's leading whitespace match the source.
Remove a extra newlines, spaces or tabs (or add a missing ones) so both sides agree.