from pathlib import Path
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"
TIER2_DIR = DATA_DIR / "tier2_historical_universe"

MASTER_FILE = (
    TIER2_DIR /
    "crsp_tier2_historical_security_master.csv"
)

DAILY_FILE = (
    DATA_DIR /
    "crsp_daily_clean.csv"
)

OUTPUT_FILE = (
    TIER2_DIR /
    "crsp_tier2_reconciliation_exceptions.csv"
)


# =============================================================================
# HELPERS
# =============================================================================

def normalize_columns(df):
    df.columns = [
        str(col).strip().lower()
        for col in df.columns
    ]
    return df


def require_columns(df, required, dataset_name):

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        print("\n" + "=" * 80)
        print(f"AVAILABLE {dataset_name.upper()} COLUMNS")
        print("=" * 80)

        print(df.columns.tolist())

        raise ValueError(
            f"Required columns missing from {dataset_name}: "
            + ", ".join(missing)
        )


# =============================================================================
# LOAD HISTORICAL SECURITY MASTER
# =============================================================================

print("=" * 80)
print("LOADING TIER 2 HISTORICAL SECURITY MASTER")
print("=" * 80)

master = pd.read_csv(
    MASTER_FILE,
    low_memory=False
)

master = normalize_columns(master)

require_columns(
    master,
    [
        "permno",
        "ticker",
        "research_classification",
    ],
    "historical security master"
)


# =============================================================================
# NORMALIZE MASTER PERMNO
# =============================================================================

master["permno"] = pd.to_numeric(
    master["permno"],
    errors="coerce"
)

master = master.loc[
    master["permno"].notna()
].copy()

master["permno"] = (
    master["permno"]
    .astype(int)
)

master_permnos = set(
    master["permno"]
    .unique()
)

print(f"Master rows: {len(master):,}")
print(f"Master PERMNOs: {len(master_permnos):,}")


# =============================================================================
# LOAD CRSP DAILY
# =============================================================================

print("\n" + "=" * 80)
print("LOADING CRSP DAILY")
print("=" * 80)

daily = pd.read_csv(
    DAILY_FILE,
    low_memory=False
)

daily = normalize_columns(daily)

require_columns(
    daily,
    [
        "permno",
        "dlycaldt",
    ],
    "CRSP Daily"
)


# =============================================================================
# NORMALIZE DAILY TYPES
# =============================================================================

daily["permno"] = pd.to_numeric(
    daily["permno"],
    errors="coerce"
)

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

daily = daily.loc[
    daily["permno"].notna()
].copy()

daily["permno"] = (
    daily["permno"]
    .astype(int)
)

daily_permnos = set(
    daily["permno"]
    .unique()
)

print(f"Daily rows: {len(daily):,}")
print(f"Daily PERMNOs: {len(daily_permnos):,}")
print(f"Daily first date: {daily['dlycaldt'].min()}")
print(f"Daily last date:  {daily['dlycaldt'].max()}")


# =============================================================================
# PERMNO RECONCILIATION
# =============================================================================

names_only = sorted(
    master_permnos -
    daily_permnos
)

daily_only = sorted(
    daily_permnos -
    master_permnos
)

matched = sorted(
    master_permnos &
    daily_permnos
)


# =============================================================================
# BUILD EXCEPTION RECORDS
# =============================================================================

rows = []


# -----------------------------------------------------------------------------
# NAMES_ONLY
# -----------------------------------------------------------------------------

for permno in names_only:

    x = master.loc[
        master["permno"] == permno
    ]

    first = x.iloc[0]

    rows.append({

        "permno": permno,

        "exception_type": "NAMES_ONLY",

        "ticker": first["ticker"],

        "research_classification":
            first["research_classification"],

        "daily_rows": 0,

        "daily_first_date": pd.NaT,

        "daily_last_date": pd.NaT,

        "resolution":
            "RETAIN_HISTORICAL_MASTER",

    })


# -----------------------------------------------------------------------------
# DAILY_ONLY
# -----------------------------------------------------------------------------

for permno in daily_only:

    x = daily.loc[
        daily["permno"] == permno
    ]

    ticker = (
        x["ticker"].dropna().iloc[0]
        if "ticker" in x.columns
        and not x["ticker"].dropna().empty
        else None
    )

    issuernm = (
        x["issuernm"].dropna().iloc[0]
        if "issuernm" in x.columns
        and not x["issuernm"].dropna().empty
        else None
    )

    securitytype = (
        x["securitytype"].dropna().iloc[0]
        if "securitytype" in x.columns
        and not x["securitytype"].dropna().empty
        else None
    )

    securitysubtype = (
        x["securitysubtype"].dropna().iloc[0]
        if "securitysubtype" in x.columns
        and not x["securitysubtype"].dropna().empty
        else None
    )

    sharetype = (
        x["sharetype"].dropna().iloc[0]
        if "sharetype" in x.columns
        and not x["sharetype"].dropna().empty
        else None
    )

    usincflg = (
        x["usincflg"].dropna().iloc[0]
        if "usincflg" in x.columns
        and not x["usincflg"].dropna().empty
        else None
    )

    rows.append({

        "permno": permno,

        "exception_type": "DAILY_ONLY",

        "ticker": ticker,

        "research_classification": None,

        "daily_rows": len(x),

        "daily_first_date": x["dlycaldt"].min(),

        "daily_last_date": x["dlycaldt"].max(),

        "issuernm": issuernm,

        "securitytype": securitytype,

        "securitysubtype": securitysubtype,

        "sharetype": sharetype,

        "usincflg": usincflg,

        "resolution":
            "EXCLUDE_UNVALIDATED_SECURITY",

    })


# =============================================================================
# CREATE EXCEPTION DATAFRAME
# =============================================================================

exceptions = pd.DataFrame(rows)


# =============================================================================
# ENSURE EXPECTED COLUMNS EXIST
# =============================================================================

expected_columns = [
    "permno",
    "exception_type",
    "ticker",
    "research_classification",
    "daily_rows",
    "daily_first_date",
    "daily_last_date",
    "issuernm",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "usincflg",
    "resolution",
]

for column in expected_columns:

    if column not in exceptions.columns:
        exceptions[column] = None


exceptions = exceptions[
    expected_columns
]


# =============================================================================
# SORT
# =============================================================================

exceptions = exceptions.sort_values(
    [
        "exception_type",
        "permno",
    ]
)


# =============================================================================
# SAVE
# =============================================================================

exceptions.to_csv(
    OUTPUT_FILE,
    index=False
)


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("TIER 2 RECONCILIATION")
print("=" * 80)

print(
    f"Historical master PERMNOs: {len(master_permnos):,}"
)

print(
    f"Daily PERMNOs:             {len(daily_permnos):,}"
)

print(
    f"Matched PERMNOs:           {len(matched):,}"
)

print(
    f"NAMES_ONLY:                {len(names_only):,}"
)

print(
    f"DAILY_ONLY:                {len(daily_only):,}"
)


print("\n" + "=" * 80)
print("TIER 2 RECONCILIATION EXCEPTIONS")
print("=" * 80)

if exceptions.empty:

    print(
        "PASS: No PERMNO reconciliation exceptions."
    )

else:

    print(
        exceptions.to_string(
            index=False
        )
    )


print("\n" + "=" * 80)
print("EXCEPTION SUMMARY")
print("=" * 80)

if exceptions.empty:

    print(
        "No exceptions."
    )

else:

    print(
        exceptions[
            "exception_type"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )


print("\n" + "=" * 80)
print("RESOLUTION")
print("=" * 80)

print(
    "NAMES_ONLY securities are retained in the historical "
    "security master because absence of Daily observations "
    "does not invalidate historical security identity."
)

print(
    "DAILY_ONLY securities remain excluded from the validated "
    "Tier 2 universe because their identity/classification "
    "has not been established through the historical master."
)

print(
    "No DAILY_ONLY security is automatically admitted based "
    "solely on Daily-file metadata."
)

print(f"\nSaved: {OUTPUT_FILE}")