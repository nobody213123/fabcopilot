from fabcopilot.infrastructure.models import Base


def test_equipment_table_matches_domain_storage_contract() -> None:
    table = Base.metadata.tables["equipment"]

    assert table.c.equipment_id.primary_key
    assert table.c.equipment_id.type.length == 64
    assert not table.c.equipment_type.nullable
    assert table.c.equipment_type.type.length == 50
    assert {constraint.name for constraint in table.constraints} >= {
        "ck_equipment_equipment_id_not_blank"
    }
