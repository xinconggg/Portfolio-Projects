from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from equity_microstructure.data.discovery import (
    discover_files,
    records_to_dicts,
)

INVENTORY_COLUMNS = [
    "path",
    "relative_path",
    "filename",
    "extension",
    "parent_directory",
    "size_bytes",
    "modified_timestamp",
    "dataset",
    "inferred_year",
    "compressed",
    "file_type",
    "hash_type",
    "hash_value",
]


@dataclass
class FileInventory:
    """Basic inventory information for one dataset file."""

    path: str
    dataset: str
    filename: str
    extension: str
    size_bytes: int
    size_mb: float
    n_columns: int
    columns: list[str]

@dataclass
class DatasetInventory:
    name: str
    path: str
    exists: bool
    size_bytes: int | None
    size_gb: float | None
    extension: str | None
    n_columns: int | None
    columns: list[str] | None

def write_file_inventory(
    root: Path,
    output_path: Path,
    project_root: Path | None = None,
    calculate_hash: bool = False,
) -> int:
    """Discover files and write their metadata to a CSV inventory."""

    records = discover_files(
        root=root,
        project_root=project_root,
        calculate_hash=calculate_hash,
    )

    rows = records_to_dicts(records)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=INVENTORY_COLUMNS,
        )
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)

def get_file_inventory(
    path: Path,
    dataset: str,
    *,
    encoding: str = "utf-8",
) -> FileInventory:
    """
    Inspect a dataset file without loading the full dataset.

    Parameters
    ----------
    path:
        Path to the dataset file.

    dataset:
        Logical dataset name, e.g. "taq", "taqm", or "crsp".

    encoding:
        File encoding used to read the header.

    Returns
    -------
    FileInventory
        Basic metadata about the file.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset file does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"Expected a file, got: {path}")

    # Read only the header.
    header = pd.read_csv(
        path,
        nrows=0,
        encoding=encoding,
    )

    size_bytes = path.stat().st_size

    return FileInventory(
        path=str(path),
        dataset=dataset,
        filename=path.name,
        extension=path.suffix.lower(),
        size_bytes=size_bytes,
        size_mb=size_bytes / (1024**2),
        n_columns=len(header.columns),
        columns=header.columns.tolist(),
    )


def inventory_to_dict(inventory: FileInventory) -> dict[str, Any]:
    """Convert a FileInventory object into a dictionary."""

    return asdict(inventory)