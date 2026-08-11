import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from fabcopilot.api.app import app
from fabcopilot.api.dependencies import get_session_factory
from fabcopilot.infrastructure.models import ApprovalRequestRecord, EquipmentRecord

pytestmark = pytest.mark.integration

EQUIPMENT_ID = "DF-AGENT-01"


def cleanup_agent_test_data() -> None:
    with get_session_factory().begin() as session:
        session.execute(
            delete(ApprovalRequestRecord).where(
                ApprovalRequestRecord.equipment_id == EQUIPMENT_ID,
            )
        )
        session.execute(
            delete(EquipmentRecord).where(
                EquipmentRecord.equipment_id == EQUIPMENT_ID,
            )
        )


def test_agent_proposal_requires_human_approval() -> None:
    cleanup_agent_test_data()

    try:
        with TestClient(app) as client:
            create_response = client.post(
                "/equipment",
                json={
                    "equipment_id": EQUIPMENT_ID,
                    "equipment_type": "diffusion_furnace",
                },
            )
            assert create_response.status_code == 201

            diagnosis_response = client.post(
                "/agent/diagnose",
                json={"prompt": f"请检查 {EQUIPMENT_ID} 的异常并建议停机"},
            )

            assert diagnosis_response.status_code == 200
            diagnosis = diagnosis_response.json()
            assert [item["name"] for item in diagnosis["tool_trace"]] == [
                "search_knowledge",
                "query_analytics",
                "propose_maintenance_action",
            ]
            assert len(diagnosis["pending_approval_ids"]) == 1
            approval_id = diagnosis["pending_approval_ids"][0]
            proposal_output = diagnosis["tool_trace"][2]["output"]
            assert proposal_output["status"] == "pending"
            assert "was not executed" in proposal_output["message"]

            pending_response = client.get(f"/approvals/{approval_id}")
            assert pending_response.status_code == 200
            assert pending_response.json()["status"] == "pending"

            decision_payload = {
                "decision": "approved",
                "decided_by": "shift-supervisor",
                "decision_note": "Alarm and maintenance evidence reviewed",
            }
            decision_response = client.post(
                f"/approvals/{approval_id}/decision",
                json=decision_payload,
            )
            assert decision_response.status_code == 200
            assert decision_response.json()["status"] == "approved"

            repeated_response = client.post(
                f"/approvals/{approval_id}/decision",
                json=decision_payload,
            )
            assert repeated_response.status_code == 409
    finally:
        cleanup_agent_test_data()
