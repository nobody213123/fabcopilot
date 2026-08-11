class EquipmentAlreadyExistsError(Exception):
    def __init__(self, equipment_id: str) -> None:
        self.equipment_id = equipment_id
        super().__init__(f"Equipment '{equipment_id}' already exists")
