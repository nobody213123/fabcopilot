from datetime import UTC, datetime, timedelta

from fabcopilot.application.services.knowledge import IndexKnowledgeDocumentService
from fabcopilot.config import Settings
from fabcopilot.domain.equipment import EquipmentType
from fabcopilot.domain.knowledge import KnowledgeDocument
from fabcopilot.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from fabcopilot.infrastructure.embeddings import HashingEmbeddingProvider
from fabcopilot.infrastructure.models import (
    AlarmEventRecord,
    EquipmentRecord,
    ProcessRunRecord,
)
from fabcopilot.infrastructure.repositories.sqlalchemy_knowledge_repository import (
    SqlAlchemyKnowledgeRepository,
)


def seed_demo_data() -> dict[str, int]:
    engine = create_database_engine(Settings().database_url)
    session_factory = create_session_factory(engine)
    reference_time = datetime(2026, 8, 1, 8, tzinfo=UTC)
    equipment_ids = ("DF-01", "DF-02")

    with session_factory.begin() as session:
        for equipment_id in equipment_ids:
            session.merge(
                EquipmentRecord(
                    equipment_id=equipment_id,
                    equipment_type=EquipmentType.DIFFUSION_FURNACE.value,
                )
            )

        yields = (0.982, 0.977, 0.941, 0.932, 0.918, 0.956)
        for index, yield_rate in enumerate(yields, start=1):
            started_at = reference_time + timedelta(hours=index * 4)
            session.merge(
                ProcessRunRecord(
                    run_id=f"DEMO-RUN-{index:02d}",
                    equipment_id="DF-01" if index <= 3 else "DF-02",
                    lot_id=f"DEMO-LOT-{index:02d}",
                    recipe="OX-1000C-DRY",
                    started_at=started_at,
                    ended_at=started_at + timedelta(hours=2),
                    yield_rate=yield_rate,
                    status="completed",
                )
            )

        alarms = (
            ("TEMP_DEVIATION", "warning", "Zone 3 temperature deviation exceeded 3 C"),
            ("O2_LOW_FLOW", "critical", "Oxygen mass flow below recipe threshold"),
            ("DOOR_SEAL", "warning", "Door seal pressure decay detected"),
        )
        for index, (code, severity, message) in enumerate(alarms, start=1):
            occurred_at = reference_time + timedelta(days=1, hours=index)
            session.merge(
                AlarmEventRecord(
                    event_id=f"DEMO-ALARM-{index:02d}",
                    equipment_id="DF-02",
                    alarm_code=code,
                    severity=severity,
                    message=message,
                    occurred_at=occurred_at,
                    cleared_at=occurred_at + timedelta(minutes=20),
                )
            )

        knowledge_service = IndexKnowledgeDocumentService(
            SqlAlchemyKnowledgeRepository(session),
            HashingEmbeddingProvider(),
        )
        documents = (
            KnowledgeDocument(
                document_id="DEMO-KB-TEMP-01",
                equipment_type=EquipmentType.DIFFUSION_FURNACE,
                title="扩散炉温区均匀性排查",
                content=(
                    "当片内均匀性恶化且 Zone 3 温差升高时，先核对热电偶漂移、"
                    "加热器输出和舟位置。未完成证据复核前不要直接修改配方。"
                ),
                source="synthetic-demo/runbook-temperature-uniformity",
            ),
            KnowledgeDocument(
                document_id="DEMO-KB-O2-01",
                equipment_type=EquipmentType.DIFFUSION_FURNACE,
                title="氧气低流量报警处置",
                content=(
                    "O2_LOW_FLOW 报警应依次检查气源压力、MFC 设定值与实际值、"
                    "阀门状态和管路泄漏。停机属于高风险动作，必须由值班主管审批。"
                ),
                source="synthetic-demo/runbook-o2-low-flow",
            ),
            KnowledgeDocument(
                document_id="DEMO-KB-SEAL-01",
                equipment_type=EquipmentType.DIFFUSION_FURNACE,
                title="炉门密封压降排查",
                content=(
                    "炉门密封压降可能来自密封圈老化、颗粒污染或压力传感器偏移。"
                    "维护前记录报警时间并与批次良率变化进行关联。"
                ),
                source="synthetic-demo/runbook-door-seal",
            ),
        )
        for document in documents:
            knowledge_service.execute(document)

    engine.dispose()
    return {"equipment": 2, "process_runs": 6, "alarms": 3, "documents": 3}


def main() -> None:
    counts = seed_demo_data()
    summary = ", ".join(f"{name}={count}" for name, count in counts.items())
    print(f"Seeded synthetic demo data: {summary}")


if __name__ == "__main__":
    main()
