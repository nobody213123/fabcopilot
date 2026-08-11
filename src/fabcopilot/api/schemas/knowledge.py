from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from fabcopilot.domain.equipment import EquipmentType


def validate_non_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("value must not be blank")
    return value


NonBlankString = Annotated[str, AfterValidator(validate_non_blank)]


class KnowledgeDocumentRequest(BaseModel):
    document_id: NonBlankString
    equipment_type: EquipmentType
    title: NonBlankString
    content: NonBlankString
    source: NonBlankString


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    equipment_type: EquipmentType
    title: str
    content: str
    source: str


class KnowledgeSearchResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document: KnowledgeDocumentResponse
    score: float
    lexical_rank: int | None
    vector_rank: int | None


SearchLimit = Annotated[int, Field(ge=1, le=20)]
