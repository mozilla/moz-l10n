


def _check_mf2(
    source_string: str, translation_string: str, context: LintContext
) -> list[Diagnostic]:
    """Android and Xcode, whose placeholders are printf specifiers and markup."""
    translation, error = parse_error.parse_mf2(translation_string, context)
    source, source_error = source_parse_error.parse_mf2(source_string, context)
    diagnostics = _gather(error, source_error)
    if translation is None:
        return diagnostics

    if format == "android":
        # Android has no way to express a deliberately blank string resource.
        diagnostics += _gather(empty_translation.check_message(translation, context))
    diagnostics += _gather(plural_source_required.check(source, translation, context))

    match = match_placeholders(format, source, translation)
    diagnostics += placeholder_not_in_reference.report(match, context)
    diagnostics += placeholder_not_in_translation.report(match, context)
    return diagnostics


def _check_gettext(
    source_string: str, translation_string: str, context: LintContext
) -> list[Diagnostic]:
    translation, error = parse_error.parse_mf2(translation_string, context)
    diagnostics: list[Diagnostic] = []
    if translation is not None:
        diagnostics += _gather(
            empty_translation.check_any_variant(translation, context)
        )
    else:
        diagnostics += _gather(error)

    if translation is not None:
        source = source_parse_error.parse_mf2_quietly(source_string)
        diagnostics += _gather(
            plural_source_required.check(source, translation, context)
        )

    diagnostics += _gather(
        trailing_newline_mismatch.check(source_string, translation_string, context)
    )
    return diagnostics


def _check_fluent(
    source_string: str, translation_string: str, context: LintContext
) -> list[Diagnostic]:
    translation = fluent_parser.parse_entry(translation_string)
    source = fluent_parser.parse_entry(source_string)

    if not isinstance(translation, (ftl.Message, ftl.Term)):
        # A comment or other well-formed but non-localizable entry gets its own
        # rule; anything else really is a syntax error.
        non_localizable = invalid_localizable_entry.check(
            translation, translation_string, context
        )
        if non_localizable is not None:
            return [non_localizable]
        if isinstance(translation, ftl.Junk):
            return _gather(
                parse_error.from_junk(translation, translation_string, context)
            )
        return []

    mismatch = message_id_mismatch.check(
        source, translation, translation_string, context
    )
    if mismatch is not None:
        return [mismatch]
    return _gather(empty_translation.check_fluent_entry(translation, context))


def _check_webext(
    source_string: str, translation_string: str, context: LintContext
) -> list[Diagnostic]:
    translation, error = parse_error.parse_mf2(translation_string, context)
    diagnostics = _gather(error)
    if not isinstance(translation, PatternMessage):
        return diagnostics

    # The reference's placeholders object is what names in the translation are
    # resolved against, so an unparsable source just leaves every name unknown.
    try:
        source = source_parse_error.parse_mf2_quietly(source_string)
        placeholders = webext_serialize_message(source)[1] if source else None
    except ValueError:
        placeholders = None

    webext_src, unsupported = placeholder_unsupported.webext_source(
        translation, context
    )
    diagnostics += unsupported

    try:
        webext_parse_message(webext_src, placeholders)
    except Exception as e:
        unknown = re.fullmatch(r"Missing placeholders entry for (\w+)", str(e))
        if unknown:
            diagnostics += _gather(
                placeholder_not_in_reference.report_placeholder(
                    f"${unknown.group(1).upper()}$", context
                )
            )
        else:
            diagnostics += _gather(parse_error.report(f"Parse error: {e}", context))
    return diagnostics
