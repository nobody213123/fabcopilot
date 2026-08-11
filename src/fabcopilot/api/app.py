from fastapi import FastAPI, HTTPException, status

from fabcopilot import __version__
from fabcopilot.api.dependencies import (
    create_equipment_service,
    get_equipment_service,
)
from fabcopilot.api.schemas.equipment import (
    EquipmentCreateRequest,
    EquipmentResponse,
)
from fabcopilot.application.exceptions import EquipmentAlreadyExistsError
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
    try:
        return create_equipment_service.execute(
            equipment_id=request.equipment_id,
            equipment_type=request.equipment_type,
        )
    except EquipmentAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@app.get("/equipment/{equipment_id}", response_model=EquipmentResponse)
def get_equipment(equipment_id: str) -> Equipment:
    equipment = get_equipment_service.execute(equipment_id)

    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    return equipment
