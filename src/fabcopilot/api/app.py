from fastapi import FastAPI, status

from fabcopilot import __version__
from fabcopilot.api.schemas.equipment import (
    EquipmentCreateRequest,
    EquipmentResponse,
)
from fabcopilot.domain.equipment import Equipment

app = FastAPI(
    title="FabCopilot",
    version=__version__,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/equipment",
    response_model=EquipmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_equipment(request: EquipmentCreateRequest) -> Equipment:
    return Equipment(
        equipment_id=request.equipment_id,
        equipment_type=request.equipment_type,
    )
