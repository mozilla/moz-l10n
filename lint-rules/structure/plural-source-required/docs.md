# `plural-source-required`

## Description

The translation is a `SelectMessage` (it has plural/variant categories such as
`one`/`other`), but the source string is a plain `PatternMessage` with no
variants. A translation may only introduce plural categories when the source
declares a selector to switch on.

## Why is this bad?

The plural categories in a translation are keyed to a selector defined by the
source. Without a source selector there is nothing to evaluate the variants
against, so the extra variants can never be selected — the translation is
structurally inconsistent with what the product will render.

## Example

```
# source.webext — a non-plural source
You have new mail.

# example.webext — translation that adds plural variants anyway
.input {$n :number}
.match $n
one {{Sinulla on {$n} uusi viesti.}}
* {{Sinulla on {$n} uutta viestiä.}}
```

The `.po` fixture pair is the negative case: a plain source with a plain
translation reports nothing.

## How to fix?

Either translate the source as a single (non-plural) string, or — if the string
genuinely needs pluralization — fix the *source* so it declares the plural
selector first.
