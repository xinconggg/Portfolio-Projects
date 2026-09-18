from __future__ import annotations

from pathlib import Path

import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_CRSP = PROJECT_ROOT / "data" / "raw" / "crsp"
PROCESSED_CRSP = PROJECT_ROOT / "data" / "processed" / "crsp"

DAILY_FILE = RAW_CRSP / "CRSP_Daily Stock File.csv"
DISTRIBUTION_FILE = RAW_CRSP / "CRSP_Distribution Information.csv"

OUTPUT_FILE = (
    PROCESSED_CRSP
    / "crsp_distribution_reconciliation.csv"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

DAILY_DATE_COL = "DlyCalDt"
DISTRIBUTION_DATE_COL = "DisExDt"

KEY_COLUMNS = ["PERMNO", "date"]

DAILY_DISTRIBUTION_COLUMNS = [
    "DisExDt",
    "DisDivAmt",
    "DisFacPr",
    "DisFacShr",
]

DISTRIBUTION_COLUMNS = [
    "PERMNO",
    "DisExDt",
    "DisSeqNbr",
    "DisType",
    "DisDivAmt",
    "DisFacPr",
    "DisFacShr",
]


# =============================================================================
# HELPERS
# =============================================================================

def normalize_date(series: pd.Series) -> pd.Series:
    """Parse CRSP dates using day-first formatting."""
    return pd.to_datetime(
        series,
        dayfirst=True,
        errors="coerce",
    )


def normalize_numeric(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Convert selected columns to numeric."""
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


def value_list(
    series: pd.Series,
) -> str:
    """Return sorted unique non-null values as a pipe-separated string."""
    values = series.dropna().unique().tolist()

    if not values:
        return ""

    values = sorted(
        values,
        key=lambda x: str(x),
    )

    return "|".join(str(x) for x in values)


def numeric_equal(
    left: pd.Series,
    right: pd.Series,
    tolerance: float = 1e-10,
) -> bool:
    """Compare two numeric series after removing missing values."""
    left_values = pd.to_numeric(
        left,
        errors="coerce",
    ).dropna()

    right_values = pd.to_numeric(
        right,
        errors="coerce",
    ).dropna()

    if len(left_values) != len(right_values):
        return False

    if len(left_values) == 0:
        return True

    return bool(
        ((left_values.sort_values().to_numpy()
          - right_values.sort_values().to_numpy())
         .__abs__() <= tolerance).all()
    )


# =============================================================================
# LOAD DAILY DATA
# =============================================================================

def load_duplicate_daily_groups() -> pd.DataFrame:
    print("=" * 80)
    print("LOADING DAILY STOCK FILE")
    print("=" * 80)

    usecols = [
        "PERMNO",
        DAILY_DATE_COL,
        *DAILY_DISTRIBUTION_COLUMNS,
        "Ticker",
    ]

    df = pd.read_csv(
        DAILY_FILE,
        usecols=usecols,
    )

    df["date"] = normalize_date(
        df[DAILY_DATE_COL]
    )

    df["PERMNO"] = pd.to_numeric(
        df["PERMNO"],
        errors="coerce",
    )

    df = normalize_numeric(
        df,
        [
            "DisDivAmt",
            "DisFacPr",
            "DisFacShr",
        ],
    )

    duplicate_mask = df.duplicated(
        subset=KEY_COLUMNS,
        keep=False,
    )

    duplicates = (
        df.loc[duplicate_mask]
        .sort_values(KEY_COLUMNS)
        .copy()
    )

    print(f"Daily rows scanned: {len(df):,}")
    print(
        "Rows belonging to duplicate groups: "
        f"{len(duplicates):,}"
    )

    print(
        "Duplicate PERMNO/date groups: "
        f"{duplicates[KEY_COLUMNS].drop_duplicates().shape[0]:,}"
    )

    return duplicates


# =============================================================================
# LOAD DISTRIBUTION DATA
# =============================================================================

def load_distributions() -> pd.DataFrame:
    print()
    print("=" * 80)
    print("LOADING DISTRIBUTION INFORMATION")
    print("=" * 80)

    df = pd.read_csv(
        DISTRIBUTION_FILE,
        usecols=DISTRIBUTION_COLUMNS,
    )

    df["DisExDt"] = normalize_date(
        df["DisExDt"]
    )

    df["PERMNO"] = pd.to_numeric(
        df["PERMNO"],
        errors="coerce",
    )

    df = normalize_numeric(
        df,
        [
            "DisSeqNbr",
            "DisDivAmt",
            "DisFacPr",
            "DisFacShr",
        ],
    )

    print(
        f"Distribution rows loaded: {len(df):,}"
    )

    return df


# =============================================================================
# RECONCILIATION
# =============================================================================

def reconcile(
    daily_duplicates: pd.DataFrame,
    distributions: pd.DataFrame,
) -> pd.DataFrame:

    rows: list[dict] = []

    grouped = daily_duplicates.groupby(
        KEY_COLUMNS,
        sort=True,
    )

    for (permno, date), daily_group in grouped:

        distribution_group = distributions[
            (distributions["PERMNO"] == permno)
            & (
                distributions["DisExDt"] == date
            )
        ].copy()

        daily_div_values = value_list(
            daily_group["DisDivAmt"]
        )

        daily_facpr_values = value_list(
            daily_group["DisFacPr"]
        )

        daily_facshr_values = value_list(
            daily_group["DisFacShr"]
        )

        dist_div_values = value_list(
            distribution_group["DisDivAmt"]
        )

        dist_facpr_values = value_list(
            distribution_group["DisFacPr"]
        )

        dist_facshr_values = value_list(
            distribution_group["DisFacShr"]
        )

        daily_div_match = (
            daily_div_values == dist_div_values
        )

        daily_facpr_match = (
            daily_facpr_values == dist_facpr_values
        )

        daily_facshr_match = (
            daily_facshr_values == dist_facshr_values
        )

        if len(distribution_group) == 0:
            status = "NO_DISTRIBUTION_MATCH"

        elif (
            daily_div_match
            and daily_facpr_match
            and daily_facshr_match
        ):
            status = "MATCH"

        elif len(distribution_group) > 1:
            status = "MULTIPLE_DISTRIBUTIONS"

        else:
            status = "VALUE_MISMATCH"

        rows.append(
            {
                "PERMNO": permno,
                "date": date,
                "Ticker": value_list(
                    daily_group["Ticker"]
                ),
                "daily_duplicate_count": len(
                    daily_group
                ),
                "daily_DisExDt": value_list(
                    daily_group["DisExDt"]
                ),
                "daily_DisDivAmt": daily_div_values,
                "daily_DisFacPr": daily_facpr_values,
                "daily_DisFacShr": daily_facshr_values,
                "distribution_match_count": len(
                    distribution_group
                ),
                "distribution_DisDivAmt":
                    dist_div_values,
                "distribution_DisFacPr":
                    dist_facpr_values,
                "distribution_DisFacShr":
                    dist_facshr_values,
                "distribution_types":
                    value_list(
                        distribution_group[
                            "DisType"
                        ]
                    ),
                "distribution_sequence_numbers":
                    value_list(
                        distribution_group[
                            "DisSeqNbr"
                        ]
                    ),
                "daily_div_match":
                    daily_div_match,
                "daily_facpr_match":
                    daily_facpr_match,
                "daily_facshr_match":
                    daily_facshr_match,
                "reconciliation_status":
                    status,
            }
        )

    return pd.DataFrame(rows)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    PROCESSED_CRSP.mkdir(
        parents=True,
        exist_ok=True,
    )

    daily_duplicates = (
        load_duplicate_daily_groups()
    )

    distributions = load_distributions()

    result = reconcile(
        daily_duplicates,
        distributions,
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("=" * 80)
    print("RECONCILIATION SUMMARY")
    print("=" * 80)

    print(
        result[
            "reconciliation_status"
        ].value_counts(dropna=False)
    )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )

    print()
    print("=" * 80)
    print("RECONCILIATION DETAILS")
    print("=" * 80)

    print(
        result.to_string(index=False)
    )


if __name__ == "__main__":
    main()