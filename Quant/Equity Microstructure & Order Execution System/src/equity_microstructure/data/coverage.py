"""Coverage inspection utilities for local research datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CoverageRecord:
    """Coverage metadata for one physical file."""

    path: str
    dataset: str

    coverage_start: str | None
    coverage_end: str | None

    number_of_unique_dates: int | None
    number_of_rows: int | None

    coverage_method: str
    status: str

    notes: str | None = None


def empty_coverage_record(
    path: Path,
    dataset: str,
) -> CoverageRecord:
    """Create an initially unknown coverage record."""

    return CoverageRecord(
        path=str(path),
        dataset=dataset,
        coverage_start=None,
        coverage_end=None,
        number_of_unique_dates=None,
        number_of_rows=None,
        coverage_method="not_inspected",
        status="pending",
        notes=None,
    )