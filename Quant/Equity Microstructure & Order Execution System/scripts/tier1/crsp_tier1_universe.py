from pathlib import Path

import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CRSP_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"

# -------------------------------------------------------------------------
# IMPORTANT:
# Replace this filename with the actual validated CRSP Names file produced
# during Phase 2.
# -------------------------------------------------------------------------
INPUT_FILE = CRSP_PROCESSED_DIR / "crsp_names_clean.csv"

OUTPUT_FILE = (
    CRSP_PROCESSED_DIR
    / "crsp_tier1_initial_universe.csv"
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names so downstream code can work consistently.
    """
    df = df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    return df


def require_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    """
    Confirm that all required columns are present.
    """
    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            "Required columns are missing from the input file:\n"
            + "\n".join(f"  - {col}" for col in missing)
        )


def clean_identifier_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean CRSP identifier columns without changing their meaning.
    """
    df = df.copy()

    for col in ["permno", "permco"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).astype("Int64")

    return df


def parse_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert CRSP date fields to pandas datetime.
    """
    df = df.copy()

    date_columns = [
        "securitybegdt",
        "securityenddt",
        "secinfostartdt",
        "secinfoenddt",
    ]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col],
                errors="coerce"
            )

    return df


# =============================================================================
# LOAD DATA
# =============================================================================

def load_crsp_names() -> pd.DataFrame:
    """
    Load the validated CRSP Names dataset.
    """
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"\nInput file not found:\n"
            f"    {INPUT_FILE}\n\n"
            "Update INPUT_FILE at the top of this script to point to "
            "the validated CRSP Names file created in Phase 2."
        )

    print("=" * 80)
    print("LOADING VALIDATED CRSP NAMES")
    print("=" * 80)
    print(f"Input: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE)

    print(f"Rows loaded: {len(df):,}")
    print(f"Columns:     {len(df.columns):,}")

    return df


# =============================================================================
# PREPARE DATA
# =============================================================================

def prepare_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize identifiers and date fields.
    """
    print("\n" + "=" * 80)
    print("PREPARING CRSP NAMES DATA")
    print("=" * 80)

    df = normalize_columns(df)

    require_columns(
        df,
        [
            "permno",
            "permco",
        ],
    )

    df = clean_identifier_columns(df)
    df = parse_date_columns(df)

    # PERMNO is mandatory for a security-level universe.
    before = len(df)

    df = df.loc[
        df["permno"].notna()
    ].copy()

    removed = before - len(df)

    print(f"Rows without PERMNO removed: {removed:,}")
    print(f"Rows retained:               {len(df):,}")
    print(f"Unique PERMNOs:               {df['permno'].nunique():,}")

    return df


# =============================================================================
# BUILD INITIAL SECURITY UNIVERSE
# =============================================================================

def build_initial_universe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build one representative row per PERMNO.

    Multiple CRSP Names records for a PERMNO are expected because security
    characteristics can change over time. For the initial universe we need
    only one security-level record.

    We retain the earliest known security information where available.
    Later Phase 3 steps will reconstruct time-varying characteristics
    from the full Names history.
    """

    print("\n" + "=" * 80)
    print("BUILDING INITIAL TIER 1 SECURITY UNIVERSE")
    print("=" * 80)

    work = df.copy()

    # Sort chronologically so the first record represents the earliest
    # available CRSP Names information for each PERMNO.
    sort_columns = ["permno"]

    if "secinfostartdt" in work.columns:
        sort_columns.append("secinfostartdt")

    work = work.sort_values(
        sort_columns,
        kind="stable"
    )

    # ---------------------------------------------------------------------
    # Columns to preserve when available.
    # ---------------------------------------------------------------------

    preferred_columns = [
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

    available_columns = [
        col for col in preferred_columns
        if col in work.columns
    ]

    universe = (
        work[available_columns]
        .drop_duplicates(
            subset=["permno"],
            keep="first"
        )
        .copy()
    )

    universe = universe.sort_values(
        "permno"
    ).reset_index(drop=True)

    print(f"Initial universe securities: {len(universe):,}")

    return universe


# =============================================================================
# VALIDATE INITIAL UNIVERSE
# =============================================================================

def validate_initial_universe(
    universe: pd.DataFrame,
    source: pd.DataFrame,
) -> None:
    """
    Validate the basic structure of the initial universe.
    """

    print("\n" + "=" * 80)
    print("VALIDATING INITIAL TIER 1 UNIVERSE")
    print("=" * 80)

    # ---------------------------------------------------------------------
    # PERMNO uniqueness
    # ---------------------------------------------------------------------

    duplicate_permnos = universe[
        universe["permno"].duplicated(keep=False)
    ]

    print(
        f"Duplicate PERMNO rows: "
        f"{len(duplicate_permnos):,}"
    )

    if len(duplicate_permnos) > 0:
        raise AssertionError(
            "Initial Tier 1 universe contains duplicate PERMNOs."
        )

    # ---------------------------------------------------------------------
    # Compare unique PERMNO counts
    # ---------------------------------------------------------------------

    source_permnos = source["permno"].nunique()
    universe_permnos = universe["permno"].nunique()

    print(f"Source unique PERMNOs:   {source_permnos:,}")
    print(f"Universe unique PERMNOs: {universe_permnos:,}")

    if source_permnos != universe_permnos:
        raise AssertionError(
            "Universe construction lost one or more PERMNOs."
        )

    # ---------------------------------------------------------------------
    # Missing PERMNO
    # ---------------------------------------------------------------------

    missing_permno = universe["permno"].isna().sum()

    print(f"Missing PERMNOs:         {missing_permno:,}")

    if missing_permno > 0:
        raise AssertionError(
            "Initial universe contains missing PERMNO values."
        )

    # ---------------------------------------------------------------------
    # PERMCO coverage
    # ---------------------------------------------------------------------

    if "permco" in universe.columns:
        missing_permco = universe["permco"].isna().sum()

        print(f"Missing PERMCOs:         {missing_permco:,}")

    print("\nBasic validation PASSED.")


# =============================================================================
# SAVE OUTPUT
# =============================================================================

def save_universe(universe: pd.DataFrame) -> None:
    """
    Save the initial Tier 1 universe.
    """

    print("\n" + "=" * 80)
    print("SAVING INITIAL TIER 1 UNIVERSE")
    print("=" * 80)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    universe.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(f"Saved: {OUTPUT_FILE}")
    print(f"Rows:  {len(universe):,}")


# =============================================================================
# SUMMARY
# =============================================================================

def print_summary(
    source: pd.DataFrame,
    universe: pd.DataFrame,
) -> None:
    """
    Print final Step 4.1 summary.
    """

    print("\n" + "=" * 80)
    print("STEP 4.1 SUMMARY")
    print("=" * 80)

    print(f"Source CRSP Names rows:       {len(source):,}")
    print(f"Source unique PERMNOs:        {source['permno'].nunique():,}")
    print(f"Initial universe securities:  {len(universe):,}")

    if "permco" in universe.columns:
        print(
            f"Unique PERMCOs:               "
            f"{universe['permco'].nunique():,}"
        )

    if "ticker" in universe.columns:
        print(
            f"Unique tickers:               "
            f"{universe['ticker'].nunique():,}"
        )

    print(f"\nOutput:")
    print(f"  {OUTPUT_FILE}")

# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    source = load_crsp_names()

    source = prepare_names(source)

    universe = build_initial_universe(source)

    validate_initial_universe(
        universe,
        source,
    )

    save_universe(universe)

    print_summary(
        source,
        universe,
    )


if __name__ == "__main__":
    main()