# `trailing-newline-mismatch`

## Description

Source and the translation must **both** end with a newline or **neither** of them should!
A mismatch in the trailing newline is not allowed.

Historically from as [Bug 1599056](https://bugzilla.mozilla.org/show_bug.cgi?id=1599056).

## Why is this bad?

The trailing newline is significant in rendering localization output. Adding or dropping it in
the translation changes the rendered string relative to the source, which can
break formatting, concatenation, or byte-for-byte expectations in consuming code.

Because the fix is purely mechanical — add or remove the final `\n` to match the
source — this rule is marked `fixable`.

## Example

```
# source.po — no trailing newline
Original

# example.po — translation adds one
Translation
<trailing newline here>
```

## How to fix?

Make the translation's trailing newline match the source: remove the extra
newline (or add the missing one) so both sides agree.
