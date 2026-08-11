import pytest
from sqlalchemy import func, select

from fabcopilot.api.dependencies import get_session_factory
from fabcopilot.demo import seed_demo_data
from fabcopilot.infrastructure.models import (
    AlarmEventRecord,
    EquipmentRecord,
    KnowledgeDocumentRecord,
    ProcessRunRecord,
)

pytestmark = pytest.mark.integration


def test_demo_seed_is_idempotent() -> None:
    first = seed_demo_data()
    second = seed_demo_data()

    assert (
        first
        == second
        == {
            "equipment": 2,
            "process_runs": 6,
            "alarms": 3,
            "documents": 3,
        }
    )
    with get_session_factory().begin() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(EquipmentRecord)
                .where(EquipmentRecord.equipment_id.like("DF-0%"))
            )
            >= 2
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ProcessRunRecord)
                .where(ProcessRunRecord.run_id.like("DEMO-RUN-%"))
            )
            == 6
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(AlarmEventRecord)
                .where(AlarmEventRecord.event_id.like("DEMO-ALARM-%"))
            )
            == 3
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(KnowledgeDocumentRecord)
                .where(KnowledgeDocumentRecord.document_id.like("DEMO-KB-%"))
            )
            == 3
        )
