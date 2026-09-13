from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DatasetProfile:
    """Aggregated profile of a large dataset."""

    path: str

    rows_scanned: int = 0

    min_date: str | None = None
    max_date: str | None = None

    unique_symbols: int = 0

    missing_values: dict[str, int] = field(default_factory=dict)

    invalid_dates: int = 0

    duplicate_rows: int = 0