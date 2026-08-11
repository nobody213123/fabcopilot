from unittest.mock import Mock, patch

from sqlalchemy import Engine

from fabcopilot.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)


def test_create_database_engine_enables_connection_health_checks() -> None:
    database_url = "postgresql+psycopg://user:password@localhost:5432/test_db"
    expected_engine = Mock(spec=Engine)

    with patch(
        "fabcopilot.infrastructure.database.create_engine",
        return_value=expected_engine,
    ) as create_engine_mock:
        engine = create_database_engine(database_url)

    assert engine is expected_engine
    create_engine_mock.assert_called_once_with(database_url, pool_pre_ping=True)


def test_create_session_factory_keeps_objects_available_after_commit() -> None:
    engine = Mock(spec=Engine)

    session_factory = create_session_factory(engine)

    assert session_factory.kw["bind"] is engine
    assert session_factory.kw["expire_on_commit"] is False
