from fabcopilot.config import Settings


def test_settings_reads_database_url_from_environment(monkeypatch) -> None:
    database_url = "postgresql+psycopg://user:password@localhost:5432/test_db"
    monkeypatch.setenv("FABCOPILOT_DATABASE_URL", database_url)
    monkeypatch.setenv("FABCOPILOT_REDIS_URL", "redis://localhost:6379/0")

    settings = Settings(_env_file=None)

    assert settings.database_url == database_url


def test_settings_treats_empty_openai_key_as_not_configured(monkeypatch) -> None:
    monkeypatch.setenv(
        "FABCOPILOT_DATABASE_URL",
        "postgresql+psycopg://user:password@localhost:5432/test_db",
    )
    monkeypatch.setenv("FABCOPILOT_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("FABCOPILOT_OPENAI_API_KEY", "")

    settings = Settings(_env_file=None)

    assert settings.openai_api_key is None


def test_settings_rejects_unknown_embedding_provider(monkeypatch) -> None:
    monkeypatch.setenv("FABCOPILOT_EMBEDDING_PROVIDER", "unknown")

    try:
        Settings(_env_file=None)
    except ValueError as exc:
        assert "embedding_provider" in str(exc)
    else:
        raise AssertionError("expected invalid embedding provider to be rejected")
