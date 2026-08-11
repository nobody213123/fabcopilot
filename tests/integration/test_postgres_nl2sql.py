from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from fabcopilot.api.app import app
from fabcopilot.application.services.natural_language_query import (
    NaturalLanguageQueryService,
)
from fabcopilot.config import Settings
from fabcopilot.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from fabcopilot.infrastructure.models import EquipmentRecord, ProcessRunRecord
from fabcopilot.infrastructure.nl2sql import (
    RuleBasedSqlGenerator,
    SqlAlchemyReadOnlyQueryExecutor,
    SqlGlotSafetyValidator,
)

pytestmark = pytest.mark.integration

EQUIPMENT_ID = "DF-NL2SQL-01"
RUN_IDS = ("RUN-NL2SQL-01", "RUN-NL2SQL-02")


def test_natural_language_query_api_returns_auditable_result() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/analytics/query",
            json={"question": "列出最近的设备报警"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["columns"] == [
        "event_id",
        "equipment_id",
        "alarm_code",
        "severity",
        "message",
        "occurred_at",
        "cleared_at",
    ]
    assert payload["sql"].startswith("SELECT event_id")
    assert "LIMIT 50" in payload["sql"]
    assert isinstance(payload["elapsed_ms"], float)


def test_natural_language_query_executes_read_only_aggregate() -> None:
    engine = create_database_engine(Settings().database_url)
    session_factory = create_session_factory(engine)
    started_at = datetime.now(UTC) - timedelta(hours=2)

    try:
        with session_factory.begin() as session:
            session.add(
                EquipmentRecord(
                    equipment_id=EQUIPMENT_ID,
                    equipment_type="diffusion_furnace",
                )
            )
            session.add_all(
                [
                    ProcessRunRecord(
                        run_id=RUN_IDS[0],
                        equipment_id=EQUIPMENT_ID,
                        lot_id="LOT-NL2SQL-01",
                        recipe="dry-oxidation",
                        started_at=started_at,
                        ended_at=started_at + timedelta(minutes=60),
                        yield_rate=Decimal("0.92000"),
                        status="completed",
                    ),
                    ProcessRunRecord(
                        run_id=RUN_IDS[1],
                        equipment_id=EQUIPMENT_ID,
                        lot_id="LOT-NL2SQL-02",
                        recipe="dry-oxidation",
                        started_at=started_at + timedelta(hours=1),
                        ended_at=started_at + timedelta(hours=2),
                        yield_rate=Decimal("0.88000"),
                        status="completed",
                    ),
                ]
            )

        with session_factory.begin() as session:
            service = NaturalLanguageQueryService(
                generator=RuleBasedSqlGenerator(),
                validator=SqlGlotSafetyValidator(),
                executor=SqlAlchemyReadOnlyQueryExecutor(session),
            )

            result = service.execute("查询各设备的平均良率")

        matching_rows = [
            row for row in result.rows if row["equipment_id"] == EQUIPMENT_ID
        ]
        assert matching_rows == [
            {
                "equipment_id": EQUIPMENT_ID,
                "average_yield": 0.9,
                "run_count": 2,
            }
        ]
        assert result.sql.endswith("LIMIT 200")
        assert not result.truncated
        assert result.elapsed_ms >= 0
    finally:
        with session_factory.begin() as session:
            session.execute(
                delete(ProcessRunRecord).where(ProcessRunRecord.run_id.in_(RUN_IDS))
            )
            session.execute(
                delete(EquipmentRecord).where(
                    EquipmentRecord.equipment_id == EQUIPMENT_ID
                )
            )
        engine.dispose()
