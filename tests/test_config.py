from fabcopilot.config import Settings


def test_settings_reads_database_url_from_environment(monkeypatch) -> None:
    database_url = "postgresql+psycopg://user:password@localhost:5432/test_db"
    monkeypatch.setenv("FABCOPILOT_DATABASE_URL", database_url)

    settings = Settings(_env_file=None)

    assert settings.database_url == database_url


def test_settings_treats_empty_openai_key_as_not_configured(monkeypatch) -> None:
    monkeypatch.setenv(
        "FABCOPILOT_DATABASE_URL",
        "postgresql+psycopg://user:password@localhost:5432/test_db",
    )
    monkeypatch.setenv("FABCOPILOT_OPENAI_API_KEY", "")

    settings = Settings(_env_file=None)

    assert settings.openai_api_key is None
