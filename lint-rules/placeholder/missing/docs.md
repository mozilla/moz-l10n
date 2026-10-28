# `placeholder.missing`

## Description

A placeholder present in the source string (e.g. `%1$s`, `%@`, `$FOO$`) does not appear in the translation or appears less often than in the source.

The diagnostic wording follows the style:
- `Placeholder %1$s not found in translation`
- `Placeholder %s has fewer occurrences in translation (expected 2, found 1)`

This is the mirror of [`placeholder.extra`](../extra/docs.md).

## Severity.WARNING

This is reported as a **warning** because a translator may legitimately drop a
placeholder in some grammatical constructions.

A dropped placeholder usually means the translation loses a dynamic value the
source intended to show (a count, a name, a link). It is often a mistake, but
because it is occasionally intentional it warns rather than blocks.

## How to fix?

Reintroduce the missing placeholder where it belongs in the translation.
If it is intentionally omitted, the warning can be acknowledged.

## Example

=== "Android XML"

    Reference:
    ``` xml
    Downloading from %1$s…
    ```
    Translation:
    ``` xml
    Herunterladen…
    ```
    > ⚠️ `Placeholder %1$s not found in translation`

    Reference:
    ``` xml
    %d of %d pages
    ```
    Translation:
    ``` xml
    %d Seiten
    ```
    > ⚠️ `Placeholder %d has fewer occurrences in translation (expected 2, found 1)`

=== "WebExtension JSON"

    Reference:
    ``` json
    Welcome back, $USER$!
    ```

    Translation:
    ``` json
    Willkommen zurück!
    ```
    > ⚠️ `Placeholder $USER$ not found in translation`

=== "MessageFormat 2"

    Reference:
    ``` mf2
    {{Downloading {$fileName} to {$folderName}…}}
    ```

    Translation:
    ``` mf2
    {{Herunterladen nach {$folderName}…}}
    ```
    > ⚠️ `Placeholder $fileName not found in translation`
