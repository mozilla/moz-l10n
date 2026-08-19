# `leading-whitespace-mismatch`

## Description

Source and the translation should **both** start with the same whitespace or **neither** of them should have any leading whitespace!

## Why is this bad?

The leading whitespace may be significant in rendering localization output.
Adding or dropping it in the translation changes the rendered string relative to the source, which can
break formatting, concatenation, or byte-for-byte expectations in consuming code.

Because the fix is purely mechanical — add or remove the final `\n` to match the
source — this rule is marked `fixable`.

## Example

```
# source.po — no leading newline
Original
```

```
# example.po — translation adds one

Translation
```

## How to fix?

Make the translation's leading whitespace match the source.
Remove an extra newline, space or tab (or add a missing one) from (or to) the start so both sides agree.