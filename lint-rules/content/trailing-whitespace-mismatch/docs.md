# `trailing-whitespace-mismatch`

## Description

Source and the translation should **both** end with the same whitespace or **neither** of them should have any trailing whitespace! A mismatch in the leading whitespace generally issues a warning whereas for `gettext` this is an **error**.

Historically from as [Bug 1599056](https://bugzilla.mozilla.org/show_bug.cgi?id=1599056).

## Why is this bad?

Generally the trailing whitespace may be significant in rendering localization output.
Adding or dropping it in the translation changes the rendered string relative to the source, which can
break formatting, concatenation, or byte-for-byte expectations in consuming code.

Specifically mismatched trailing newlines break `gettext` compilation!
So with this format this will be an ERROR!

Because the fix is purely mechanical — add or remove the final `\n` to match the
source — this rule is marked `fixable`.

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
Remove an extra newline, space or tab (or add a missing one) from (or to) the end so both sides agree.
