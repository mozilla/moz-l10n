# `source-parse-error`

## Description

The *source*, the reference the translation is derived from, could not
be parsed. This is reported as a **warning** rather than an error because the
problem is not the translator's fault, and it deliberately does not block the
translation from being saved.

In Pontoon this surfaces as `Source parse error: <detail>` for the Android and
Xcode (MF2-backed) formats. When the source cannot be parsed, downstream
comparison rules such as [`placeholder-not-in-translation`](../../placeholders/placeholder-not-in-translation/docs.md)
cannot run reliably.

## Why is this bad?

A malformed source string usually points at a bug in the reference resource or
in the import pipeline. Surfacing it as a warning gives the team a signal to fix
the reference without penalizing translators or blocking their work.

## Example

```xml
<!-- source.xml — an unterminated placeholder in the reference -->
<string name="greeting">Hello {$name</string>
```

The translation itself (`example.xml`) parses fine.

## How to fix?

Correct the source resource so it parses. This typically requires a change to
the reference project, not to the translation.
