from dataclasses import dataclass

from fabcopilot.domain.equipment import EquipmentType


@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    equipment_type: EquipmentType
    title: str
    content: str
    source: str

    def __post_init__(self) -> None:
        for field_name in ("document_id", "title", "content", "source"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be blank")


@dataclass(frozen=True)
class KnowledgeSearchResult:
    document: KnowledgeDocument
    score: float
    lexical_rank: int | None
    vector_rank: int | None
