from __future__ import annotations

from pathlib import Path

import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_CRSP = PROJECT_ROOT / "data" / "raw" / "crsp"
PROCESSED_CRSP = PROJECT_ROOT / "data" / "processed" / "crsp"

NAMES_FILE = RAW_CRSP / "CRSP_Names.csv"
DAILY_FILE = PROCESSED_CRSP / "crsp_daily_clean.csv"

RECON_FILE = (
    PROCESSED_CRSP
    / "crsp_tier1_daily_reconciliation.csv"
)

OUTPUT_FILE = (
    PROCESSED_CRSP
    / "crsp_tier1_discrepancy_investigation.csv"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

REQUIRED_NAME_COLUMNS = [
    "permno",
    "permco",
    "ticker",
    "cusip",
    "issuernm",
    "shareclass",
    "usincflg",
    "issuertype",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "siccd",
    "primaryexch",
    "tradingstatusflg",
    "tradingsymbol",
    "naics",
    "securitybegdt",
    "securityenddt",
]


# =============================================================================
# HELPERS
# =============================================================================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize CRSP Names column names to lowercase.

    The raw CRSP Names file supplied in this project uses lowercase
    column names.
    """

    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    return df


def parse_date(series: pd.Series) -> pd.Series:
    """
    Parse CRSP date fields using day-first format.

    The supplied CRSP Names file contains dates such as:
        18/5/2012
    """

    return pd.to_datetime(
        series,
        errors="coerce",
        dayfirst=True,
    )


def print_section(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


# =============================================================================
# LOAD DATA
# =============================================================================

def load_names() -> pd.DataFrame:

    print_section("LOADING CRSP NAMES")

    names = pd.read_csv(
        NAMES_FILE,
        low_memory=False,
    )

    names = normalize_columns(names)

    print(f"Rows loaded: {len(names):,}")
    print(f"Columns loaded: {len(names.columns)}")

    missing = [
        col
        for col in REQUIRED_NAME_COLUMNS
        if col not in names.columns
    ]

    if missing:
        raise ValueError(
            f"CRSP Names is missing required columns: {missing}"
        )

    names["permno"] = pd.to_numeric(
        names["permno"],
        errors="coerce",
    )

    names["permco"] = pd.to_numeric(
        names["permco"],
        errors="coerce",
    )

    names["securitybegdt"] = parse_date(
        names["securitybegdt"]
    )

    names["securityenddt"] = parse_date(
        names["securityenddt"]
    )

    return names


def load_daily() -> pd.DataFrame:

    print_section("LOADING CLEAN CRSP DAILY")

    daily = pd.read_csv(
        DAILY_FILE,
        low_memory=False,
    )

    daily.columns = [
        str(c).strip()
        for c in daily.columns
    ]

    daily["PERMNO"] = pd.to_numeric(
        daily["PERMNO"],
        errors="coerce",
    )

    daily["PERMCO"] = pd.to_numeric(
        daily["PERMCO"],
        errors="coerce",
    )

    daily["DlyCalDt"] = pd.to_datetime(
        daily["DlyCalDt"],
        errors="coerce"
        )

    print(f"Rows loaded: {len(daily):,}")
    print(
        f"Unique PERMNOs: "
        f"{daily['PERMNO'].nunique():,}"
    )
    
    expected_first_date = pd.Timestamp("1993-01-04")
    expected_last_date = pd.Timestamp("2018-12-31")

    actual_first_date = daily["DlyCalDt"].min()
    actual_last_date = daily["DlyCalDt"].max()

    print()
    print(
        f"Daily first date: {actual_first_date.date()}"
    )
    print(
        f"Daily last date:  {actual_last_date.date()}"
    )

    if actual_first_date != expected_first_date:
        raise ValueError(
            "Unexpected earliest daily date: "
            f"{actual_first_date.date()} "
            f"(expected {expected_first_date.date()})"
        )

    if actual_last_date != expected_last_date:
        raise ValueError(
            "Unexpected latest daily date: "
            f"{actual_last_date.date()} "
            f"(expected {expected_last_date.date()})"
        )

    print("PASS   Daily date range matches validated clean file.")

    return daily


def load_reconciliation() -> pd.DataFrame:

    print_section("LOADING TIER 1 RECONCILIATION")

    recon = pd.read_csv(
        RECON_FILE,
        low_memory=False,
    )

    recon["PERMNO"] = pd.to_numeric(
        recon["PERMNO"],
        errors="coerce",
    )

    print(f"Rows loaded: {len(recon):,}")

    return recon


# =============================================================================
# IDENTIFY DISCREPANCIES
# =============================================================================

def identify_discrepancies(
    recon: pd.DataFrame,
) -> pd.DataFrame:

    print_section("IDENTIFYING DISCREPANCIES")

    discrepancies = recon.loc[
        recon["reconciliation_status"]
        .isin(
            [
                "NAMES_ONLY",
                "DAILY_ONLY",
            ]
        )
    ].copy()

    discrepancies = discrepancies.sort_values(
        "PERMNO"
    )

    print(
        f"Discrepant PERMNOs: "
        f"{len(discrepancies):,}"
    )

    print()

    print(
        discrepancies[
            [
                "PERMNO",
                "reconciliation_status",
            ]
        ].to_string(index=False)
    )

    return discrepancies


# =============================================================================
# INVESTIGATE NAMES HISTORY
# =============================================================================

def investigate_names_history(
    names: pd.DataFrame,
    permnos: list[int],
) -> pd.DataFrame:

    print_section("INVESTIGATING CRSP NAMES HISTORY")

    subset = names.loc[
        names["permno"].isin(permnos)
    ].copy()

    if subset.empty:
        return pd.DataFrame()

    display_columns = [
        "permno",
        "permco",
        "ticker",
        "cusip",
        "issuernm",
        "shareclass",
        "usincflg",
        "issuertype",
        "securitytype",
        "securitysubtype",
        "sharetype",
        "siccd",
        "primaryexch",
        "tradingstatusflg",
        "tradingsymbol",
        "naics",
        "securitybegdt",
        "securityenddt",
    ]

    display_columns = [
        c
        for c in display_columns
        if c in subset.columns
    ]

    print(
        subset[
            display_columns
        ].to_string(index=False)
    )

    return subset


# =============================================================================
# INVESTIGATE DAILY HISTORY
# =============================================================================

def investigate_daily_history(
    daily: pd.DataFrame,
    permnos: list[int],
) -> pd.DataFrame:

    print_section("INVESTIGATING DAILY HISTORY")

    subset = daily.loc[
        daily["PERMNO"].isin(permnos)
    ].copy()

    if subset.empty:
        return pd.DataFrame()

    summary = (
        subset
        .groupby("PERMNO")
        .agg(
            daily_first_date=(
                "DlyCalDt",
                "min",
            ),
            daily_last_date=(
                "DlyCalDt",
                "max",
            ),
            daily_observations=(
                "DlyCalDt",
                "size",
            ),
            unique_permco=(
                "PERMCO",
                "nunique",
            ),
            unique_tickers=(
                "Ticker",
                "nunique",
            ),
        )
        .reset_index()
    )

    print(
        summary.to_string(index=False)
    )

    return summary


# =============================================================================
# DATE OVERLAP ANALYSIS
# =============================================================================

def analyze_date_overlap(
    names: pd.DataFrame,
    daily: pd.DataFrame,
    permnos: list[int],
) -> pd.DataFrame:

    print_section("ANALYZING NAMES / DAILY DATE OVERLAP")

    rows: list[dict] = []

    for permno in permnos:

        name_rows = names.loc[
            names["permno"] == permno
        ].copy()

        daily_rows = daily.loc[
            daily["PERMNO"] == permno
        ].copy()

        name_start = (
            name_rows["securitybegdt"].min()
            if not name_rows.empty
            else pd.NaT
        )

        name_end = (
            name_rows["securityenddt"].max()
            if not name_rows.empty
            else pd.NaT
        )

        daily_start = (
            daily_rows["DlyCalDt"].min()
            if not daily_rows.empty
            else pd.NaT
        )

        daily_end = (
            daily_rows["DlyCalDt"].max()
            if not daily_rows.empty
            else pd.NaT
        )

        if (
            pd.notna(name_start)
            and pd.notna(daily_end)
            and pd.notna(name_end)
            and pd.notna(daily_start)
        ):
            overlap_start = max(
                name_start,
                daily_start,
            )

            overlap_end = min(
                name_end,
                daily_end,
            )

            date_overlap = (
                overlap_start <= overlap_end
            )

        else:
            overlap_start = pd.NaT
            overlap_end = pd.NaT
            date_overlap = False

        rows.append(
            {
                "PERMNO": permno,
                "names_first_date": name_start,
                "names_last_date": name_end,
                "daily_first_date": daily_start,
                "daily_last_date": daily_end,
                "overlap_start": overlap_start,
                "overlap_end": overlap_end,
                "date_range_overlap": date_overlap,
            }
        )

    result = pd.DataFrame(rows)

    print(
        result.to_string(index=False)
    )

    return result


# =============================================================================
# CLASSIFICATION
# =============================================================================

def classify_discrepancies(
    discrepancies: pd.DataFrame,
    names: pd.DataFrame,
    daily: pd.DataFrame,
) -> pd.DataFrame:

    print_section("CLASSIFYING DISCREPANCIES")

    results = []

    for _, row in discrepancies.iterrows():

        permno = int(row["PERMNO"])
        status = row["reconciliation_status"]

        name_rows = names.loc[
            names["permno"] == permno
        ]

        daily_rows = daily.loc[
            daily["PERMNO"] == permno
        ]

        name_start = (
            name_rows["securitybegdt"].min()
            if not name_rows.empty
            else pd.NaT
        )

        name_end = (
            name_rows["securityenddt"].max()
            if not name_rows.empty
            else pd.NaT
        )

        daily_start = (
            daily_rows["DlyCalDt"].min()
            if not daily_rows.empty
            else pd.NaT
        )

        daily_end = (
            daily_rows["DlyCalDt"].max()
            if not daily_rows.empty
            else pd.NaT
        )

        if status == "NAMES_ONLY":

            classification = (
                "NAMES_NO_DAILY_HISTORY"
            )

            explanation = (
                "Security exists in CRSP Names but "
                "has no observation in the supplied "
                "clean daily file."
            )

        elif status == "DAILY_ONLY":

            classification = (
                "DAILY_NO_NAMES_RECORD"
            )

            explanation = (
                "Security has daily observations but "
                "is absent from the supplied CRSP Names "
                "file."
            )

        else:

            classification = "UNCLASSIFIED"
            explanation = ""

        results.append(
            {
                "PERMNO": permno,
                "reconciliation_status": status,
                "classification": classification,
                "explanation": explanation,
                "names_first_date": name_start,
                "names_last_date": name_end,
                "daily_first_date": daily_start,
                "daily_last_date": daily_end,
            }
        )

    result = pd.DataFrame(results)

    print(
        result.to_string(index=False)
    )

    return result


# =============================================================================
# SAVE
# =============================================================================

def save_investigation(
    result: pd.DataFrame,
) -> None:

    print_section("WRITING INVESTIGATION OUTPUT")

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(
        f"Saved: {OUTPUT_FILE}"
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    names = load_names()
    daily = load_daily()
    recon = load_reconciliation()

    discrepancies = identify_discrepancies(
        recon
    )

    permnos = (
        discrepancies["PERMNO"]
        .dropna()
        .astype(int)
        .tolist()
    )

    names_history = investigate_names_history(
        names,
        permnos,
    )

    daily_history = investigate_daily_history(
        daily,
        permnos,
    )

    date_overlap = analyze_date_overlap(
        names,
        daily,
        permnos,
    )

    classification = classify_discrepancies(
        discrepancies,
        names,
        daily,
    )

    # Merge the main investigative outputs.
    result = classification.merge(
        date_overlap,
        on="PERMNO",
        how="left",
        suffixes=(
            "",
            "_overlap",
        ),
    )

    # Add selected Names metadata.
    if not names_history.empty:

        metadata_columns = [
            "permno",
            "permco",
            "ticker",
            "cusip",
            "issuernm",
            "securitytype",
            "securitysubtype",
            "sharetype",
            "primaryexch",
            "tradingstatusflg",
            "securitybegdt",
            "securityenddt",
        ]

        metadata_columns = [
            c
            for c in metadata_columns
            if c in names_history.columns
        ]

        metadata = (
            names_history[
                metadata_columns
            ]
            .drop_duplicates("permno")
            .rename(
                columns={
                    "permno": "PERMNO",
                }
            )
        )

        result = result.merge(
            metadata,
            on="PERMNO",
            how="left",
        )

    save_investigation(result)

    print_section("FINAL SUMMARY")

    print(
        f"Discrepant PERMNOs: "
        f"{len(result):,}"
    )

    print()

    print(
        result[
            [
                "PERMNO",
                "reconciliation_status",
                "classification",
                "date_range_overlap",
            ]
        ].to_string(index=False)
    )

    print()
    print(
        "Investigation complete."
    )


if __name__ == "__main__":
    main()