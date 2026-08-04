# `parse-error`

## Description

The translation could not be parsed from its resource format.
Any translation that reaches this state cannot be serialized back into the resource.

In Pontoon this surfaces as `Parse error: <detail>` for the MF2-backed formats
and as the underlying parser's annotation message for Fluent (`ast.Junk`).

## Why is this bad?

An un-parseable translation is unusable: it cannot be written to the resource
file and would break the build or the running product. This is the most severe
class of problem a linter can catch and must always block submission.

## Example

```ftl
# example.ftl — a Fluent message with no value or attributes
key =
```

## How to fix?

Fix the syntax reported in the diagnostic. For the example above, give the
message a value:

```ftl
key = Some value
```
