import pytest

from fabcopilot.domain.equipment import EquipmentType
from fabcopilot.domain.knowledge import KnowledgeDocument


@pytest.mark.parametrize("field_name", ["document_id", "title", "content", "source"])
def test_knowledge_document_rejects_blank_required_fields(field_name: str) -> None:
    values = {
        "document_id": "doc-01",
        "equipment_type": EquipmentType.DIFFUSION_FURNACE,
        "title": "Temperature non-uniformity",
        "content": "Check thermocouple drift and heater zones.",
        "source": "maintenance-manual",
    }
    values[field_name] = "  "

    with pytest.raises(ValueError, match=f"{field_name} must not be blank"):
        KnowledgeDocument(**values)
