from pathlib import Path
import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"

HISTORICAL_UNIVERSE_FILE = (
    DATA_DIR / "crsp_tier1_historical_universe.csv"
)

NAMES_FILE = (
    DATA_DIR / "crsp_names_clean.csv"
)

DAILY_FILE = (
    DATA_DIR / "crsp_daily_clean.csv"
)

RECONCILIATION_FILE = (
    DATA_DIR / "crsp_tier1_daily_reconciliation.csv"
)

EXCLUSIONS_FILE = (
    DATA_DIR / "crsp_tier1_universe_exclusions.csv"
)

OUTPUT_FILE = (
    DATA_DIR / "crsp_tier1_historical_universe_validation.csv"
)


# =============================================================================
# RESEARCH WINDOW
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-04")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def normalize_columns(df):
    """
    Standardize all column names.

    Every column name is:
        1. converted to string
        2. stripped of whitespace
        3. converted to lowercase
    """

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return df


def normalize_permno(df):
    """
    Normalize permno after column names have been lowercased.
    """

    df = df.copy()

    if "permno" in df.columns:
        df["permno"] = pd.to_numeric(
            df["permno"],
            errors="coerce"
        ).astype("Int64")

    return df


def load_csv(path):
    """
    Load a CSV and immediately normalize its column names.
    """

    df = pd.read_csv(
        path,
        low_memory=False
    )

    df = normalize_columns(df)
    df = normalize_permno(df)

    return df


# =============================================================================
# LOAD FILES
# =============================================================================

section("LOADING HISTORICAL TIER 1 UNIVERSE")

universe = load_csv(HISTORICAL_UNIVERSE_FILE)
names = load_csv(NAMES_FILE)
daily = load_csv(DAILY_FILE)
reconciliation = load_csv(RECONCILIATION_FILE)
exclusions = load_csv(EXCLUSIONS_FILE)

print(f"Historical universe rows: {len(universe):,}")
print(f"Historical universe permnos: {universe['permno'].nunique():,}")

print(f"Names rows: {len(names):,}")
print(f"Daily rows: {len(daily):,}")
print(f"Reconciliation rows: {len(reconciliation):,}")
print(f"Exclusion rows: {len(exclusions):,}")


# =============================================================================
# DISPLAY COLUMN NAMES
# =============================================================================

section("CHECKING COLUMN NAMES")

print("Historical universe columns:")
print(universe.columns.tolist())

print()
print("Names columns:")
print(names.columns.tolist())

print()
print("Daily columns:")
print(daily.columns.tolist())

print()
print("Reconciliation columns:")
print(reconciliation.columns.tolist())

print()
print("Exclusion columns:")
print(exclusions.columns.tolist())


# =============================================================================
# REQUIRED COLUMN CHECK
# =============================================================================

section("CHECKING REQUIRED COLUMNS")

required_universe_columns = [
    "permno",
]

missing_required = [
    col
    for col in required_universe_columns
    if col not in universe.columns
]

if missing_required:
    raise ValueError(
        "Historical universe is missing required columns: "
        + ", ".join(missing_required)
    )

print("PASS   Required historical-universe columns present.")


# =============================================================================
# PREPARE DATE COLUMNS
# =============================================================================

section("PREPARING DATE COLUMNS")

date_columns = [
    "securitybegdt",
    "securityenddt",
    "secinfostartdt",
    "secinfoenddt",
    "daily_first_date",
    "daily_last_date",
]

for col in date_columns:

    if col in universe.columns:

        universe[col] = pd.to_datetime(
            universe[col],
            errors="coerce"
        )

        print(f"Parsed: {col}")


# =============================================================================
# BASIC STRUCTURAL VALIDATION
# =============================================================================

section("BASIC STRUCTURAL VALIDATION")

duplicate_permnos = universe[
    universe["permno"].duplicated(keep=False)
]

missing_permno = universe["permno"].isna().sum()

print(
    f"Duplicate permno rows: {len(duplicate_permnos):,}"
)

print(
    f"Missing permno values: {missing_permno:,}"
)

print(
    f"Unique permnos: {universe['permno'].nunique():,}"
)

if len(duplicate_permnos) == 0 and missing_permno == 0:

    print(
        "PASS   permno structural validation passed."
    )

else:

    print(
        "FAIL   permno structural validation failed."
    )


# =============================================================================
# REQUIRED IDENTIFIER VALIDATION
# =============================================================================

section("VALIDATING REQUIRED IDENTIFIERS")

required_columns = [
    "permno",
    "permco",
]

for col in required_columns:

    if col not in universe.columns:

        print(
            f"FAIL   Missing required column: {col}"
        )

        continue

    missing = universe[col].isna().sum()

    print(
        f"{col} missing values: {missing:,}"
    )


# =============================================================================
# DAILY HISTORY COVERAGE
# =============================================================================

section("VALIDATING DAILY HISTORY COVERAGE")

if "permno" not in daily.columns:

    raise ValueError(
        "Daily file does not contain required column: permno"
    )

daily_permnos = set(
    daily["permno"]
    .dropna()
    .astype(int)
)

universe_permnos = set(
    universe["permno"]
    .dropna()
    .astype(int)
)

missing_daily = sorted(
    universe_permnos - daily_permnos
)

print(
    f"Universe permnos: {len(universe_permnos):,}"
)

print(
    f"Permnos with daily history: "
    f"{len(universe_permnos & daily_permnos):,}"
)

print(
    f"Universe permnos missing daily history: "
    f"{len(missing_daily):,}"
)

if missing_daily:

    print(
        "Missing daily-history permnos:"
    )

    print(missing_daily)

    print(
        "FAIL   Daily-history coverage failed."
    )

else:

    print(
        "PASS   All historical-universe securities "
        "have daily history."
    )


# =============================================================================
# DAILY DATE RANGE VALIDATION
# =============================================================================

section("VALIDATING DAILY DATE RANGE")

if {
    "daily_first_date",
    "daily_last_date",
}.issubset(universe.columns):

    before_start = universe[
        universe["daily_first_date"] < RESEARCH_START
    ]

    after_end = universe[
        universe["daily_last_date"] > RESEARCH_END
    ]

    print(
        f"Daily histories beginning before research start: "
        f"{len(before_start):,}"
    )

    print(
        f"Daily histories extending beyond research end: "
        f"{len(after_end):,}"
    )

    if len(before_start) == 0 and len(after_end) == 0:

        print(
            "PASS   Daily history lies within research window."
        )

    else:

        print(
            "INFO   Daily history metadata extends outside "
            "the research window."
        )

else:

    print(
        "INFO   Daily date-range metadata is not available "
        "in the historical universe file."
    )


# =============================================================================
# HISTORICAL OVERLAP VALIDATION
# =============================================================================

section("VALIDATING HISTORICAL DATE OVERLAP")

overlap_columns = {
    "securitybegdt",
    "securityenddt",
    "daily_first_date",
    "daily_last_date",
}

invalid_overlap = pd.DataFrame()

if overlap_columns.issubset(universe.columns):

    universe["historical_overlap_start"] = universe[
        [
            "securitybegdt",
            "daily_first_date",
        ]
    ].max(axis=1)

    universe["historical_overlap_end"] = universe[
        [
            "securityenddt",
            "daily_last_date",
        ]
    ].min(axis=1)

    universe["valid_historical_overlap"] = (
        universe["historical_overlap_start"]
        <= universe["historical_overlap_end"]
    )

    invalid_overlap = universe[
        ~universe["valid_historical_overlap"]
    ]

    print(
        f"Valid historical overlaps: "
        f"{universe['valid_historical_overlap'].sum():,}"
    )

    print(
        f"Invalid historical overlaps: "
        f"{len(invalid_overlap):,}"
    )

    if len(invalid_overlap) == 0:

        print(
            "PASS   Historical overlap validation passed."
        )

    else:

        print(
            "FAIL   Invalid historical overlaps detected."
        )

        print(
            invalid_overlap[
                [
                    "permno",
                    "securitybegdt",
                    "securityenddt",
                    "daily_first_date",
                    "daily_last_date",
                ]
            ].to_string(index=False)
        )

else:

    print(
        "INFO   Required date columns for overlap validation "
        "are not available."
    )


# =============================================================================
# SECURITY TYPE VALIDATION
# =============================================================================

section("VALIDATING SECURITY TYPES")

security_type_columns = [
    "securitytype",
    "securitysubtype",
    "sharetype",
    "usincflg",
    "issuertype",
]

for col in security_type_columns:

    if col not in universe.columns:
        continue

    print()
    print(f"{col}:")

    print(
        universe[col]
        .value_counts(dropna=False)
        .to_string()
    )


# =============================================================================
# ETF / FUND CHECK
# =============================================================================

section("CHECKING FOR ETF / FUND CONTAMINATION")

etf_fund = pd.DataFrame()

if "securitysubtype" in universe.columns:

    etf_fund = universe[
        universe["securitysubtype"]
        .astype(str)
        .str.upper()
        .isin(
            [
                "ETF",
                "CEF",
                "FUND",
            ]
        )
    ]

    print(
        f"ETF/FUND securities in historical universe: "
        f"{len(etf_fund):,}"
    )

    if len(etf_fund) > 0:

        print(
            "Potential ETF/FUND contamination detected:"
        )

        display_columns = [
            "permno",
            "permco",
            "ticker",
            "securitytype",
            "securitysubtype",
            "issuertype",
        ]

        display_columns = [
            col
            for col in display_columns
            if col in etf_fund.columns
        ]

        print(
            etf_fund[
                display_columns
            ].to_string(index=False)
        )

    else:

        print(
            "PASS   No ETF/FUND securities detected."
        )


# =============================================================================
# EXCLUSION CROSS-CHECK
# =============================================================================

section("CROSS-CHECKING EXCLUSIONS")

contamination = []

if "permno" in exclusions.columns:

    exclusion_permnos = set(
        exclusions["permno"]
        .dropna()
        .astype(int)
    )

    contamination = sorted(
        universe_permnos
        &
        exclusion_permnos
    )

    print(
        f"Excluded permnos: "
        f"{len(exclusion_permnos):,}"
    )

    print(
        f"Excluded permnos appearing in universe: "
        f"{len(contamination):,}"
    )

    if contamination:

        print(
            "FAIL   Excluded securities appear "
            "in historical universe:"
        )

        print(contamination)

    else:

        print(
            "PASS   No excluded permnos appear "
            "in historical universe."
        )

else:

    print(
        "INFO   Exclusion file does not contain permno."
    )


# =============================================================================
# RECONCILIATION CROSS-CHECK
# =============================================================================

section("CROSS-CHECKING RECONCILIATION")

missing_reconciliation = []

if "permno" in reconciliation.columns:

    reconciliation_permnos = set(
        reconciliation["permno"]
        .dropna()
        .astype(int)
    )

    missing_reconciliation = sorted(
        universe_permnos
        -
        reconciliation_permnos
    )

    print(
        f"Historical universe permnos missing "
        f"from reconciliation: "
        f"{len(missing_reconciliation):,}"
    )

    if missing_reconciliation:

        print(
            missing_reconciliation
        )

        print(
            "FAIL   Some historical-universe securities "
            "are absent from reconciliation."
        )

    else:

        print(
            "PASS   All historical-universe securities "
            "are represented in reconciliation."
        )

else:

    print(
        "INFO   Reconciliation file does not contain permno."
    )


# =============================================================================
# NAMES CROSS-CHECK
# =============================================================================

section("CROSS-CHECKING CRSP NAMES")

if "permno" not in names.columns:

    raise ValueError(
        "CRSP Names file does not contain required column: permno"
    )

names_permnos = set(
    names["permno"]
    .dropna()
    .astype(int)
)

missing_names = sorted(
    universe_permnos
    -
    names_permnos
)

print(
    f"Historical universe permnos missing "
    f"from CRSP Names: "
    f"{len(missing_names):,}"
)

if missing_names:

    print(missing_names)

    print(
        "FAIL   Names coverage failed."
    )

else:

    print(
        "PASS   All historical-universe securities "
        "have CRSP Names records."
    )


# =============================================================================
# TICKER / CUSIP INFORMATION
# =============================================================================

section("IDENTIFIER DIVERSITY CHECK")

for col in [
    "ticker",
    "cusip",
]:

    if col not in universe.columns:
        continue

    missing = universe[col].isna().sum()

    unique_values = universe[
        col
    ].nunique(
        dropna=True
    )

    print(
        f"{col}: "
        f"unique={unique_values:,}, "
        f"missing={missing:,}"
    )


# =============================================================================
# UNIVERSE SUMMARY
# =============================================================================

section("HISTORICAL TIER 1 UNIVERSE SUMMARY")

summary = {
    "historical_universe_rows":
        len(universe),

    "unique_permnos":
        universe["permno"].nunique(),

    "unique_permcos":
        (
            universe["permco"].nunique()
            if "permco" in universe.columns
            else None
        ),

    "unique_tickers":
        (
            universe["ticker"].nunique()
            if "ticker" in universe.columns
            else None
        ),

    "missing_permno":
        int(missing_permno),

    "duplicate_permno_rows":
        int(len(duplicate_permnos)),

    "missing_daily_history":
        int(len(missing_daily)),

    "invalid_historical_overlap":
        int(len(invalid_overlap)),

    "etf_fund_count":
        int(len(etf_fund)),

    "excluded_permno_contamination":
        int(len(contamination)),

    "missing_reconciliation":
        int(len(missing_reconciliation)),

    "missing_names":
        int(len(missing_names)),
}

summary_df = pd.DataFrame(
    [summary]
)


# =============================================================================
# FINAL VALIDATION STATUS
# =============================================================================

section("FINAL VALIDATION STATUS")

checks = {
    "duplicate_permnos":
        len(duplicate_permnos) == 0,

    "missing_permno":
        missing_permno == 0,

    "missing_daily_history":
        len(missing_daily) == 0,

    "invalid_overlap":
        len(invalid_overlap) == 0,

    "exclusion_contamination":
        len(contamination) == 0,

    "missing_reconciliation":
        len(missing_reconciliation) == 0,

    "missing_names":
        len(missing_names) == 0,
}

for check_name, passed in checks.items():

    status = "PASS" if passed else "FAIL"

    print(
        f"{status:<6} {check_name}"
    )


all_passed = all(
    checks.values()
)

print()

if all_passed:

    print(
        "Historical Tier 1 universe "
        "passed all validation checks."
    )

else:

    print(
        "Review validation failures before "
        "continuing."
    )


# =============================================================================
# SAVE VALIDATION SUMMARY
# =============================================================================

section("SAVING VALIDATION SUMMARY")

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

summary_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"Saved: {OUTPUT_FILE}"
)