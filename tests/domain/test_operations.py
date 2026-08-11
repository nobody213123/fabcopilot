from datetime import UTC, datetime, timedelta

import pytest

from fabcopilot.domain.operations import ProcessRun, ProcessRunStatus


def test_process_run_rejects_yield_outside_ratio_range() -> None:
    with pytest.raises(ValueError, match="yield_rate must be between 0 and 1"):
        ProcessRun(
            run_id="RUN-01",
            equipment_id="DF-01",
            lot_id="LOT-01",
            recipe="dry-oxidation",
            started_at=datetime.now(UTC),
            status=ProcessRunStatus.COMPLETED,
            yield_rate=1.01,
        )


def test_process_run_rejects_invalid_time_order() -> None:
    started_at = datetime.now(UTC)

    with pytest.raises(ValueError, match="ended_at must be after started_at"):
        ProcessRun(
            run_id="RUN-01",
            equipment_id="DF-01",
            lot_id="LOT-01",
            recipe="dry-oxidation",
            started_at=started_at,
            ended_at=started_at - timedelta(minutes=1),
            status=ProcessRunStatus.COMPLETED,
            yield_rate=0.95,
        )
