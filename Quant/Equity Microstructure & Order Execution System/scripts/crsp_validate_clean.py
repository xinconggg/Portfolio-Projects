from __future__ import annotations

from pathlib import Path

import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CLEAN_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_daily_clean.csv"
)


# =============================================================================
# EXPECTED VALUES
# =============================================================================

EXPECTED_ROWS = 184_041
EXPECTED_PERMNOS = 41
EXPECTED_DATES = 6_547

EXPECTED_FIRST_DATE = pd.Timestamp("1993-01-04")
EXPECTED_LAST_DATE = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPERS
# =============================================================================

def section(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def check(condition: bool, label: str) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"{status:<6} {label}")

    if not condition:
        raise AssertionError(f"Validation failed: {label}")


# =============================================================================
# MAIN VALIDATION
# =============================================================================

def main() -> None:

    section("LOADING CLEAN CRSP DAILY FILE")

    if not CLEAN_FILE.exists():
        raise FileNotFoundError(
            f"Clean CRSP file does not exist:\n{CLEAN_FILE}"
        )

    df = pd.read_csv(
        CLEAN_FILE,
        low_memory=False,
    )

    print(f"File: {CLEAN_FILE}")
    print(f"Rows loaded: {len(df):,}")
    print(f"Columns loaded: {len(df.columns)}")

    # -------------------------------------------------------------------------
    # ROW COUNT
    # -------------------------------------------------------------------------

    section("ROW COUNT")

    print(f"Rows: {len(df):,}")

    check(
        len(df) == EXPECTED_ROWS,
        f"Expected {EXPECTED_ROWS:,} rows",
    )

    # -------------------------------------------------------------------------
    # REQUIRED COLUMNS
    # -------------------------------------------------------------------------

    section("REQUIRED COLUMNS")

    required_columns = [
        "PERMNO",
        "PERMCO",
        "YYYYMMDD",
        "DlyCalDt",
        "DlyPrc",
        "DlyRet",
        "DlyRetx",
        "DlyVol",
        "DlyClose",
        "DlyLow",
        "DlyHigh",
        "DlyBid",
        "DlyAsk",
        "DlyOpen",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    print(f"Missing required columns: {len(missing_columns)}")

    if missing_columns:
        for column in missing_columns:
            print(f"  - {column}")

    check(
        len(missing_columns) == 0,
        "All required columns are present",
    )

    # -------------------------------------------------------------------------
    # QUALITY FLAG COLUMNS
    # -------------------------------------------------------------------------

    section("QUALITY FLAG COLUMNS")

    flag_columns = [
        column
        for column in df.columns
        if column.startswith("quality_")
    ]

    print(f"Quality flag columns: {len(flag_columns)}")

    for column in flag_columns:
        print(f"  - {column}")

    print(
    f"Quality flag columns present in clean file: "
    f"{len(flag_columns)}"
)

    if flag_columns:
        print("WARNING  Diagnostic quality flags are present in clean file")
    else:
        print("PASS     Clean file contains no diagnostic quality flag columns")

    # -------------------------------------------------------------------------
    # DATE VALIDATION
    # -------------------------------------------------------------------------

    section("DATE VALIDATION")

    df["clean_date"] = pd.to_datetime(
        df["DlyCalDt"],
        errors="coerce",
    )

    invalid_dates = df["clean_date"].isna().sum()

    print(f"Invalid DlyCalDt values: {invalid_dates:,}")

    check(
        invalid_dates == 0,
        "No invalid DlyCalDt values",
    )

    # -------------------------------------------------------------------------
    # YYYYMMDD VALIDATION
    # -------------------------------------------------------------------------

    parsed_yyyymmdd = pd.to_datetime(
        df["YYYYMMDD"].astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    invalid_yyyymmdd = parsed_yyyymmdd.isna().sum()

    print(f"Invalid YYYYMMDD values: {invalid_yyyymmdd:,}")

    check(
        invalid_yyyymmdd == 0,
        "No invalid YYYYMMDD values",
    )

    # -------------------------------------------------------------------------
    # DATE AGREEMENT
    # -------------------------------------------------------------------------

    disagreements = (
        parsed_yyyymmdd != df["clean_date"]
    ).sum()

    print(
        f"YYYYMMDD / DlyCalDt disagreements: "
        f"{disagreements:,}"
    )

    check(
        disagreements == 0,
        "YYYYMMDD agrees with DlyCalDt",
    )

    # -------------------------------------------------------------------------
    # DATE RANGE
    # -------------------------------------------------------------------------

    earliest = df["clean_date"].min()
    latest = df["clean_date"].max()

    print(f"Earliest date: {earliest}")
    print(f"Latest date:   {latest}")

    check(
        earliest == EXPECTED_FIRST_DATE,
        f"Earliest date is {EXPECTED_FIRST_DATE.date()}",
    )

    check(
        latest == EXPECTED_LAST_DATE,
        f"Latest date is {EXPECTED_LAST_DATE.date()}",
    )

    # -------------------------------------------------------------------------
    # PERMNO VALIDATION
    # -------------------------------------------------------------------------

    section("PERMNO VALIDATION")

    missing_permno = df["PERMNO"].isna().sum()
    invalid_permno = (df["PERMNO"] <= 0).sum()
    unique_permnos = df["PERMNO"].nunique()

    print(f"Missing PERMNO:       {missing_permno:,}")
    print(f"Invalid PERMNO <= 0:  {invalid_permno:,}")
    print(f"Unique PERMNOs:       {unique_permnos:,}")

    check(
        missing_permno == 0,
        "No missing PERMNO",
    )

    check(
        invalid_permno == 0,
        "No invalid PERMNO",
    )

    check(
        unique_permnos == EXPECTED_PERMNOS,
        f"Expected {EXPECTED_PERMNOS} unique PERMNOs",
    )

    # -------------------------------------------------------------------------
    # PERMNO / PERMCO
    # -------------------------------------------------------------------------

    section("PERMNO / PERMCO RELATIONSHIP")

    permco_counts = (
        df.groupby("PERMNO")["PERMCO"]
        .nunique()
    )

    multiple_permco = permco_counts[
        permco_counts > 1
    ]

    print(
        "PERMNOs with >1 PERMCO: "
        f"{len(multiple_permco):,}"
    )

    if len(multiple_permco) > 0:
        print(multiple_permco)

    check(
        len(multiple_permco) == 0,
        "Every PERMNO maps to at most one PERMCO",
    )

    # -------------------------------------------------------------------------
    # KEY UNIQUENESS
    # -------------------------------------------------------------------------

    section("PERMNO / DATE KEY UNIQUENESS")

    duplicate_mask = df.duplicated(
        subset=["PERMNO", "clean_date"],
        keep=False,
    )

    duplicate_rows = duplicate_mask.sum()

    duplicate_groups = (
        df.loc[duplicate_mask]
        .groupby(["PERMNO", "clean_date"])
        .ngroups
    )

    print(f"Rows in duplicate groups: {duplicate_rows:,}")
    print(f"Duplicate PERMNO/date groups: {duplicate_groups:,}")

    check(
        duplicate_rows == 0,
        "No duplicate PERMNO/date observations",
    )

    # -------------------------------------------------------------------------
    # DATE COUNT
    # -------------------------------------------------------------------------

    section("DATE COVERAGE")

    unique_dates = df["clean_date"].nunique()

    print(f"Unique dates: {unique_dates:,}")

    check(
        unique_dates == EXPECTED_DATES,
        f"Expected {EXPECTED_DATES:,} unique dates",
    )

    # -------------------------------------------------------------------------
    # PRICE VALIDATION
    # -------------------------------------------------------------------------

    section("PRICE VALIDATION")

    for column in [
        "DlyPrc",
        "DlyClose",
        "DlyLow",
        "DlyHigh",
        "DlyOpen",
    ]:
        missing = df[column].isna().sum()
        nonpositive = (
            (df[column] <= 0)
            .fillna(False)
            .sum()
        )

        print(
            f"{column:<12} "
            f"missing={missing:,} "
            f"nonpositive={nonpositive:,}"
        )

        check(
            nonpositive == 0,
            f"{column} has no non-positive values",
        )

    # Low / high relationship
    low_high_invalid = (
        (df["DlyLow"] > df["DlyHigh"])
        .fillna(False)
        .sum()
    )

    # Open outside low/high
    open_invalid = (
        (
            (df["DlyOpen"] < df["DlyLow"])
            | (df["DlyOpen"] > df["DlyHigh"])
        )
        .fillna(False)
        .sum()
    )

    # Close outside low/high
    close_invalid = (
        (
            (df["DlyClose"] < df["DlyLow"])
            | (df["DlyClose"] > df["DlyHigh"])
        )
        .fillna(False)
        .sum()
    )

    print(f"Low > High:            {low_high_invalid:,}")
    print(f"Open outside Low/High: {open_invalid:,}")
    print(f"Close outside Low/High:{close_invalid:,}")

    check(
        low_high_invalid == 0,
        "No Low > High observations",
    )

    check(
        open_invalid == 0,
        "No Open outside Low/High",
    )

    check(
        close_invalid == 0,
        "No Close outside Low/High",
    )

    # -------------------------------------------------------------------------
    # BID / ASK
    # -------------------------------------------------------------------------

    section("BID / ASK VALIDATION")

    bid_ask_invalid = (
        (df["DlyBid"] > df["DlyAsk"])
        .fillna(False)
        .sum()
    )

    print(
        f"Bid > Ask observations: "
        f"{bid_ask_invalid:,}"
    )

    print(
        "NOTE: Bid > Ask observations are retained "
        "and treated as diagnostic quality flags."
    )

    # -------------------------------------------------------------------------
    # TRADING ACTIVITY
    # -------------------------------------------------------------------------

    section("TRADING ACTIVITY")

    negative_volume = (
        (df["DlyVol"] < 0)
        .fillna(False)
        .sum()
    )

    negative_trades = (
        (df["DlyNumTrd"] < 0)
        .fillna(False)
        .sum()
    )

    print(f"Negative DlyVol:     {negative_volume:,}")
    print(f"Negative DlyNumTrd:  {negative_trades:,}")

    check(
        negative_volume == 0,
        "No negative volume",
    )

    check(
        negative_trades == 0,
        "No negative trade counts",
    )

    # -------------------------------------------------------------------------
    # CORPORATE ACTION PRESERVATION
    # -------------------------------------------------------------------------

    section("CORPORATE ACTION FIELD PRESERVATION")

    corporate_action_columns = [
        "DisExDt",
        "DisDivAmt",
        "DisFacPr",
        "DisFacShr",
    ]

    for column in corporate_action_columns:
        check(
            column in df.columns,
            f"{column} preserved",
        )

    # -------------------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------------------

    section("FINAL VALIDATION SUMMARY")

    print(f"Rows:                 {len(df):,}")
    print(f"Unique PERMNOs:       {unique_permnos:,}")
    print(f"Unique dates:         {unique_dates:,}")
    print(f"Duplicate keys:       {duplicate_rows:,}")
    print(f"Earliest date:        {earliest.date()}")
    print(f"Latest date:          {latest.date()}")
    print()
    print("CLEAN CRSP DAILY FILE VALIDATION PASSED.")
    print()
    print(
        "The cleaned dataset is structurally valid and ready "
        "for downstream Phase 3 universe construction."
    )


if __name__ == "__main__":
    main()