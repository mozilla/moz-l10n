# `placeholder.unsupported`

## Description

While checking a WebExtension (`messages.json`) translation, a placeholder was
encountered that carries no serializable `source` attribute, so it cannot be
turned back into valid WebExtension placeholder syntax.

This is closely related to [`parse-error`](../../syntax/parse-error/docs.md) but
is specific to the WebExtension placeholder model, where each placeholder in the
message text must map to an entry with a concrete `$...$` / `$n` source form.

## Why is this bad?

WebExtension messages store placeholders in a separate `placeholders` object and
reference them from the message. A placeholder the serializer cannot express
means the resulting `messages.json` would be invalid or lose the substitution.

## Example

A translation whose message part is an expression with no string `source`
attribute, e.g. an expression carrying only a non-string argument. Because this
depends on internal message construction rather than a literal snippet, the
example here is illustrative; see
[`test_custom.py`](../../../../pontoon/checks/tests/test_custom.py) for the
WebExtension placeholder cases.

## How to fix?

Use a supported WebExtension placeholder that has an explicit source form
(`$1`, `$FOO$`, …) matching the reference, or write the value as literal text.
