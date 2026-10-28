# `placeholder.extra`

## Description

The translation contains an additional placeholder (e.g. `%1$s`, `%@`, `$FOO$`) that does not appear in the source string or it appears more often in the translation than in the source.

The diagnostic wording follows the style:
- `Placeholder %@ not found in reference`
- `Placeholder %s has more occurrences in translation (expected 1, found 2)`

This is the mirror of [`placeholder.missing`](../missing/docs.md).

## Severity.ERROR

Placeholders are substituted at runtime with values the source declares.
A placeholder that the source does not provide will be rendered literally or,
might point to some variable that's never declared and so for some formatters,
crash the format call.

## How to fix?

Remove the placeholder that has no counterpart in the source,
correct it to match the source one or if it's genuinely needed,
request a fix in the source.

## Example

=== "Android XML"

    Reference:
    ``` xml
    Downloading from %1$s…
    ```
    Translation:
    ``` xml
    Herunterladen von %1…
    ```
    > 🚫 `Placeholder %1 not found in reference`

    Reference:
    ```xml
    %s files found
    ```
    Translation:

    ``` xml
    %s von %s Dateien gefunden
    ```
    > 🚫 `Placeholder %s has more occurrences in translation (expected 1, found 2)`

=== "WebExtension JSON"

    Reference:
    ``` json
    Backup created successfully.
    ```
    Translation:
    ``` json
    Backup für $USER$ erfolgreich erstellt.
    ```
    > 🚫 `Placeholder $USER$ not found in reference`
