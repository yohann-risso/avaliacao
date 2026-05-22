from security import public_error_message, redact_sensitive


def test_redact_sensitive_masks_database_urls_and_tokens():
    text = (
        "Falha em APP_DATABASE_URL=postgresql://postgres.proj:SenhaMuitoForte@host:5432/postgres "
        "com Authorization: Bearer abc.def.ghi e password=aberta"
    )

    redacted = redact_sensitive(text)

    assert "SenhaMuitoForte" not in redacted
    assert "postgres.proj" not in redacted
    assert "abc.def.ghi" not in redacted
    assert "aberta" not in redacted
    assert "APP_DATABASE_URL=***" in redacted
    assert "Bearer ***" in redacted
    assert "password=***" in redacted


def test_public_error_message_only_exposes_validation_errors():
    assert public_error_message(ValueError("senha=abc"), "fallback") == "senha=***"
    assert public_error_message(RuntimeError("password=abc"), "fallback") == "fallback"
