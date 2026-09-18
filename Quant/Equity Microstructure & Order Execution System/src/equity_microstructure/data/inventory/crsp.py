from __future__ import annotations

from pathlib import Path

import pandas as pd

from equity_microstructure.data.inventory.inventory import (
    get_file_inventory,
)


CRSP_FILE_ROLES = {
    "CRSP_Daily Stock File.csv": "daily_security",
    "CRSP_Daily Stock Market Indexes.csv": "daily_market_index",
    "CRSP_Delisting Information.csv": "delisting_information",
    "CRSP_Distribution Information.csv": "distribution_information",
    "CRSP_Monthly Stock File.csv": "monthly_security",
    "CRSP_Monthly Stock Market Indexes.csv": "monthly_market_index",
    "CRSP_Names.csv": "security_names",
    "CRSP_Share Outstanding.csv": "share_outstanding",
}


def classify_crsp_file(
    filename: str,
    columns: list[str],
) -> dict[str, str]:
    """
    Classify a CRSP extract using its filename and observed columns.

    This classification describes the supplied extract itself.
    It does not imply that the file should be merged into another
    CRSP dataset.
    """

    role = CRSP_FILE_ROLES.get(
        filename,
        "unknown_crsp_extract",
    )

    column_set = set(columns)

    date_candidates = [
        column
        for column in columns
        if column.lower().endswith("dt")
        or column.lower().endswith("date")
        or "caldt" in column.lower()
        or column.lower() == "yyyymmdd"
    ]

    identifier_candidates = [
        column
        for column in columns
        if column.upper() in {
            "PERMNO",
            "PERMCO",
            "CUSIP",
            "CUSIP9",
            "TICKER",
        }
    ]

    if "PERMNO" in column_set:
        identifier_candidates = [
            "PERMNO",
            *[
                column
                for column in identifier_candidates
                if column != "PERMNO"
            ],
        ]

    return {
        "role": role,
        "date_candidates": "|".join(date_candidates),
        "identifier_candidates": "|".join(identifier_candidates),
    }


def build_crsp_inventory(
    raw_crsp_dir: Path,
) -> pd.DataFrame:
    """
    Build a lightweight inventory of CRSP CSV extracts.

    Only CSV headers are read. The full datasets are not loaded.
    """

    raw_crsp_dir = Path(raw_crsp_dir)

    if not raw_crsp_dir.exists():
        raise FileNotFoundError(
            f"CRSP directory does not exist: {raw_crsp_dir}"
        )

    if not raw_crsp_dir.is_dir():
        raise ValueError(
            f"Expected a directory, got: {raw_crsp_dir}"
        )

    rows: list[dict[str, object]] = []

    for path in sorted(raw_crsp_dir.glob("*.csv")):
        inventory = get_file_inventory(
            path=path,
            dataset="crsp",
        )

        classification = classify_crsp_file(
            filename=inventory.filename,
            columns=inventory.columns,
        )

        rows.append(
            {
                "dataset": inventory.dataset,
                "filename": inventory.filename,
                "path": inventory.path,
                "size_bytes": inventory.size_bytes,
                "size_mb": round(inventory.size_mb, 2),
                "n_columns": inventory.n_columns,
                "columns": "|".join(inventory.columns),
                **classification,
            }
        )

    return pd.DataFrame(rows)


def write_crsp_inventory(
    raw_crsp_dir: Path,
    output_path: Path,
) -> pd.DataFrame:
    """Build and write the CRSP inventory to CSV."""

    inventory = build_crsp_inventory(
        raw_crsp_dir=raw_crsp_dir,
    )

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    inventory.to_csv(
        output_path,
        index=False,
    )

    return inventory