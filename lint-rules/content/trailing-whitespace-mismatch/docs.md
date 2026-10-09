# `trailing-whitespace-mismatch`

## Description

Source and translation should **both** end with the same whitespace or **neither** of them should have any trailing whitespace.

A mismatch in the trailing whitespace generally issues a warning whereas for `gettext` this is an **error**.

## Why is this bad?

Trailing whitespace may be significant in rendering localization output.
Adding or dropping it in the translation changes the rendered string relative to the source, which can
break formatting, concatenation, or byte-for-byte expectations in consuming code.

Specifically for `gettext`: Mismatched trailing newlines break compilation! See [bugzilla #1599056](https://bugzilla.mozilla.org/show_bug.cgi?id=1599056)

## Example

```
# source.po — no trailing newline
Original
```

```
# example.po — translation adds one
Translation

```

## How to fix?

Make the translation's trailing whitespace match the source.
Remove a extra newlines, spaces or tabs (or add missing ones) so both sides agree.
