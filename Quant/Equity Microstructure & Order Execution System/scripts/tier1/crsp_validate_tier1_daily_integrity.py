from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"


DAILY_FILE = DATA_DIR / "crsp_tier1_daily.csv"
UNIVERSE_FILE = DATA_DIR / "crsp_tier1_eligible_universe.csv"

OUTPUT_SUMMARY = DATA_DIR / "crsp_tier1_daily_integrity_summary.csv"
OUTPUT_SECURITY = DATA_DIR / "crsp_tier1_daily_integrity_security_summary.csv"


RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def normalize_permno(series):
    return pd.to_numeric(series, errors="coerce").astype("Int64")


# =============================================================================
# LOAD DATA
# =============================================================================

section("LOADING TIER 1 DAILY DATASET")

daily = pd.read_csv(DAILY_FILE, low_memory=False)
print(f"Rows loaded:        {len(daily):,}")
print(f"Columns loaded:     {len(daily.columns)}")


section("LOADING ELIGIBLE TIER 1 UNIVERSE")

universe = pd.read_csv(UNIVERSE_FILE, low_memory=False)
print(f"Eligible rows:      {len(universe):,}")


# =============================================================================
# NORMALIZE COLUMN NAMES
# =============================================================================

section("NORMALIZING COLUMN NAMES")

daily.columns = daily.columns.str.strip().str.lower()
universe.columns = universe.columns.str.strip().str.lower()

print("PASS   Column names standardized to lowercase.")


# =============================================================================
# REQUIRED COLUMN VALIDATION
# =============================================================================

section("VALIDATING REQUIRED COLUMNS")

required_daily = [
    "permno",
    "dlycaldt",
    "dlyprc",
    "dlyvol",
    "dlybid",
    "dlyask",
    "dlyopen",
    "dlyhigh",
    "dlylow",
    "dlyclose",
    "dlyret",
    "dlyretx",
    "dlyfacprc",
]

missing_daily = sorted(set(required_daily) - set(daily.columns))

if missing_daily:
    raise ValueError(
        f"Missing required daily columns: {missing_daily}"
    )

if "permno" not in universe.columns:
    raise ValueError("Eligible universe does not contain permno.")

print("PASS   Required daily integrity columns present.")
print("PASS   Eligible universe contains permno.")


# =============================================================================
# PREPARE IDENTIFIERS AND DATES
# =============================================================================

section("PREPARING DATA")

daily["permno"] = normalize_permno(daily["permno"])
universe["permno"] = normalize_permno(universe["permno"])

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

for col in [
    "dlyprc",
    "dlyvol",
    "dlybid",
    "dlyask",
    "dlyopen",
    "dlyhigh",
    "dlylow",
    "dlyclose",
    "dlyret",
    "dlyretx",
    "dlyfacprc",
]:
    daily[col] = pd.to_numeric(daily[col], errors="coerce")

print("PASS   Identifiers, dates, and numeric fields prepared.")


# =============================================================================
# BASIC DATE VALIDATION
# =============================================================================

section("VALIDATING DAILY DATES")

invalid_dates = daily["dlycaldt"].isna().sum()

print(f"Invalid DlyCalDt values: {invalid_dates}")

if invalid_dates != 0:
    raise ValueError("Invalid daily dates detected.")

print(
    f"Daily date range: "
    f"{daily['dlycaldt'].min().date()} to "
    f"{daily['dlycaldt'].max().date()}"
)


# =============================================================================
# PRICE INTEGRITY
# =============================================================================

section("VALIDATING PRICE INTEGRITY")

price_fields = [
    "dlyprc",
    "dlyopen",
    "dlyhigh",
    "dlylow",
    "dlyclose",
]

price_results = {}

for col in price_fields:

    negative = (daily[col] < 0).sum()
    zero = (daily[col] == 0).sum()
    missing = daily[col].isna().sum()

    price_results[f"{col}_negative"] = int(negative)
    price_results[f"{col}_zero"] = int(zero)
    price_results[f"{col}_missing"] = int(missing)

    print(
        f"{col:<12} "
        f"negative={negative:,} "
        f"zero={zero:,} "
        f"missing={missing:,}"
    )


# =============================================================================
# HIGH / LOW / OPEN / CLOSE CONSISTENCY
# =============================================================================

section("CHECKING OHLC CONSISTENCY")

ohlc_available = daily[
    ["dlyopen", "dlyhigh", "dlylow", "dlyclose"]
].notna().all(axis=1)

high_below_low = (
    ohlc_available
    & (daily["dlyhigh"] < daily["dlylow"])
)

open_outside_range = (
    ohlc_available
    & (
        (daily["dlyopen"] < daily["dlylow"])
        | (daily["dlyopen"] > daily["dlyhigh"])
    )
)

close_outside_range = (
    ohlc_available
    & (
        (daily["dlyclose"] < daily["dlylow"])
        | (daily["dlyclose"] > daily["dlyhigh"])
    )
)

print(
    f"High below low observations:       "
    f"{high_below_low.sum():,}"
)

print(
    f"Open outside high/low range:       "
    f"{open_outside_range.sum():,}"
)

print(
    f"Close outside high/low range:      "
    f"{close_outside_range.sum():,}"
)


# =============================================================================
# VOLUME INTEGRITY
# =============================================================================

section("VALIDATING VOLUME")

volume_missing = daily["dlyvol"].isna().sum()
volume_zero = (daily["dlyvol"] == 0).sum()
volume_negative = (daily["dlyvol"] < 0).sum()

print(f"Missing volume observations:       {volume_missing:,}")
print(f"Zero-volume observations:          {volume_zero:,}")
print(f"Negative-volume observations:      {volume_negative:,}")

if volume_negative == 0:
    print("PASS   No negative volume detected.")
else:
    print("WARNING   Negative volume detected.")


# =============================================================================
# RETURN INTEGRITY
# =============================================================================

section("VALIDATING RETURN FIELDS")

return_fields = ["dlyret", "dlyretx"]

for col in return_fields:

    missing = daily[col].isna().sum()
    positive_one = (daily[col] > 1).sum()
    negative_one = (daily[col] < -1).sum()

    print(
        f"{col:<10} "
        f"missing={missing:,} "
        f"> +100%={positive_one:,} "
        f"< -100%={negative_one:,}"
    )


# =============================================================================
# RETURN OUTLIER DIAGNOSTICS
# =============================================================================

section("IDENTIFYING RETURN OUTLIERS")

RETURN_THRESHOLD = 0.50

return_outlier = (
    daily["dlyret"].abs() > RETURN_THRESHOLD
)

print(
    f"Observations with |DlyRet| > "
    f"{RETURN_THRESHOLD:.0%}: {return_outlier.sum():,}"
)

if return_outlier.any():

    print("\nLargest absolute return observations:")

    outlier_display = (
        daily.loc[
            return_outlier,
            ["permno", "dlycaldt", "dlyprc", "dlyret"]
        ]
        .assign(abs_return=lambda x: x["dlyret"].abs())
        .sort_values("abs_return", ascending=False)
        .head(20)
    )

    print(
        outlier_display[
            ["permno", "dlycaldt", "dlyprc", "dlyret"]
        ].to_string(index=False)
    )


# =============================================================================
# PRICE JUMP DIAGNOSTIC
# =============================================================================

section("IDENTIFYING LARGE PRICE JUMPS")

daily = daily.sort_values(
    ["permno", "dlycaldt"]
).reset_index(drop=True)

daily["previous_price"] = (
    daily.groupby("permno")["dlyprc"]
    .shift(1)
)

daily["price_change"] = (
    daily["dlyprc"] / daily["previous_price"] - 1
)

PRICE_JUMP_THRESHOLD = 0.50

price_jump = (
    daily["previous_price"].notna()
    & daily["dlyprc"].notna()
    & (daily["price_change"].abs() > PRICE_JUMP_THRESHOLD)
)

print(
    f"Price changes exceeding "
    f"{PRICE_JUMP_THRESHOLD:.0%}: "
    f"{price_jump.sum():,}"
)


# =============================================================================
# ADJUSTED PRICE DIAGNOSTIC
# =============================================================================

section("VALIDATING ADJUSTED PRICE FIELD")

adjusted_price_missing = daily["dlyfacprc"].isna().sum()
adjusted_price_nonpositive = (
    daily["dlyfacprc"] <= 0
).sum()

print(
    f"Missing adjusted price factor:     "
    f"{adjusted_price_missing:,}"
)

print(
    f"Non-positive adjusted price factor: "
    f"{adjusted_price_nonpositive:,}"
)


# =============================================================================
# BID / ASK DIAGNOSTIC
# =============================================================================

section("VALIDATING BID / ASK FIELDS")

both_quotes = (
    daily["dlybid"].notna()
    & daily["dlyask"].notna()
)

bid_only = (
    daily["dlybid"].notna()
    & daily["dlyask"].isna()
)

ask_only = (
    daily["dlybid"].isna()
    & daily["dlyask"].notna()
)

crossed = (
    both_quotes
    & (daily["dlybid"] > daily["dlyask"])
)

zero_bid = (
    daily["dlybid"].notna()
    & (daily["dlybid"] == 0)
)

zero_ask = (
    daily["dlyask"].notna()
    & (daily["dlyask"] == 0)
)

print(f"Observations with both bid and ask: {both_quotes.sum():,}")
print(f"Bid-only observations:              {bid_only.sum():,}")
print(f"Ask-only observations:              {ask_only.sum():,}")
print(f"Crossed bid/ask observations:        {crossed.sum():,}")
print(f"Zero bid observations:               {zero_bid.sum():,}")
print(f"Zero ask observations:               {zero_ask.sum():,}")


# =============================================================================
# KEY EXECUTION-FIELD MISSINGNESS
# =============================================================================

section("CHECKING KEY EXECUTION-FIELD MISSINGNESS")

execution_fields = [
    "dlyprc",
    "dlyvol",
    "dlybid",
    "dlyask",
    "dlyopen",
    "dlyhigh",
    "dlylow",
    "dlyclose",
    "dlyret",
]

for col in execution_fields:

    missing = daily[col].isna().sum()
    pct = missing / len(daily) if len(daily) else np.nan

    print(
        f"{col:<10} "
        f"missing={missing:,} "
        f"({pct:.2%})"
    )


# =============================================================================
# SECURITY-LEVEL INTEGRITY SUMMARY
# =============================================================================

section("BUILDING SECURITY-LEVEL INTEGRITY SUMMARY")

eligible_permnos = set(
    universe["permno"].dropna().astype(int)
)

security_rows = []

for permno, group in daily.groupby("permno"):

    observations = len(group)

    row = {
        "permno": int(permno),
        "observations": observations,
        "first_date": group["dlycaldt"].min(),
        "last_date": group["dlycaldt"].max(),

        "missing_price": int(group["dlyprc"].isna().sum()),
        "zero_price": int((group["dlyprc"] == 0).sum()),
        "negative_price": int((group["dlyprc"] < 0).sum()),

        "missing_volume": int(group["dlyvol"].isna().sum()),
        "zero_volume": int((group["dlyvol"] == 0).sum()),
        "negative_volume": int((group["dlyvol"] < 0).sum()),

        "missing_bid": int(group["dlybid"].isna().sum()),
        "missing_ask": int(group["dlyask"].isna().sum()),

        "crossed_quote_rows": int(
            (
                group["dlybid"].notna()
                & group["dlyask"].notna()
                & (group["dlybid"] > group["dlyask"])
            ).sum()
        ),

        "return_missing": int(group["dlyret"].isna().sum()),

        "return_outlier_rows": int(
            (group["dlyret"].abs() > RETURN_THRESHOLD).sum()
        ),

        "price_jump_rows": int(
            (
                group["dlyprc"]
                .div(group["dlyprc"].shift(1))
                .sub(1)
                .abs()
                > PRICE_JUMP_THRESHOLD
            ).sum()
        ),

        "ohlc_inconsistency_rows": int(
            (
                (
                    group["dlyhigh"] < group["dlylow"]
                )
                |
                (
                    (group["dlyopen"] < group["dlylow"])
                    |
                    (group["dlyopen"] > group["dlyhigh"])
                )
                |
                (
                    (group["dlyclose"] < group["dlylow"])
                    |
                    (group["dlyclose"] > group["dlyhigh"])
                )
            ).sum()
        ),
    }

    row["eligible_universe"] = permno in eligible_permnos

    security_rows.append(row)


security_summary = pd.DataFrame(security_rows)


# =============================================================================
# SECURITY SUMMARY VALIDATION
# =============================================================================

section("VALIDATING SECURITY-LEVEL INTEGRITY SUMMARY")

summary_permnos = set(
    security_summary["permno"].astype(int)
)

missing_security_summary = eligible_permnos - summary_permnos
unexpected_security_summary = summary_permnos - eligible_permnos

print(
    f"Eligible securities:              "
    f"{len(eligible_permnos)}"
)

print(
    f"Security summary securities:      "
    f"{len(summary_permnos)}"
)

print(
    f"Missing securities:               "
    f"{len(missing_security_summary)}"
)

print(
    f"Unexpected securities:            "
    f"{len(unexpected_security_summary)}"
)

if not missing_security_summary and not unexpected_security_summary:
    print(
        "PASS   Security-level summary exactly "
        "matches eligible universe."
    )


# =============================================================================
# OVERALL INTEGRITY STATISTICS
# =============================================================================

section("OVERALL INTEGRITY STATISTICS")

print(
    f"Total observations:               "
    f"{len(daily):,}"
)

print(
    f"Total securities:                  "
    f"{daily['permno'].nunique():,}"
)

print(
    f"Missing price rows:                "
    f"{daily['dlyprc'].isna().sum():,}"
)

print(
    f"Zero price rows:                   "
    f"{(daily['dlyprc'] == 0).sum():,}"
)

print(
    f"Missing volume rows:               "
    f"{daily['dlyvol'].isna().sum():,}"
)

print(
    f"Zero volume rows:                  "
    f"{(daily['dlyvol'] == 0).sum():,}"
)

print(
    f"Return outlier rows:               "
    f"{return_outlier.sum():,}"
)

print(
    f"Large price-jump rows:             "
    f"{price_jump.sum():,}"
)

print(
    f"OHLC inconsistency rows:           "
    f"{(
        high_below_low
        | open_outside_range
        | close_outside_range
    ).sum():,}"
)

print(
    f"Crossed quote rows:                "
    f"{crossed.sum():,}"
)


# =============================================================================
# BUILD VALIDATION FLAGS
# =============================================================================

section("FINAL INTEGRITY VALIDATION")

validation = {}

validation["no_negative_price"] = (
    (daily["dlyprc"] < 0).sum() == 0
)

validation["no_negative_volume"] = (
    (daily["dlyvol"] < 0).sum() == 0
)

validation["no_negative_bid"] = (
    (daily["dlybid"] < 0).sum() == 0
)

validation["no_negative_ask"] = (
    (daily["dlyask"] < 0).sum() == 0
)

validation["ohlc_structure_valid"] = (
    (
        high_below_low
        | open_outside_range
        | close_outside_range
    ).sum() == 0
)

validation["no_missing_daily_dates"] = (
    invalid_dates == 0
)

validation["security_summary_complete"] = (
    len(missing_security_summary) == 0
    and len(unexpected_security_summary) == 0
)

validation["eligible_permnos_complete"] = (
    set(daily["permno"].dropna().astype(int))
    == eligible_permnos
)

validation["all_within_research_window"] = (
    daily["dlycaldt"].between(
        RESEARCH_START,
        RESEARCH_END
    ).all()
)


for name, passed in validation.items():

    if passed:
        print(f"PASS   {name}")
    else:
        print(f"FAIL   {name}")


# Crossed quotes and return/price outliers remain diagnostics.
diagnostic_flags = {
    "crossed_quotes_diagnostic": int(crossed.sum()),
    "return_outliers_diagnostic": int(return_outlier.sum()),
    "price_jumps_diagnostic": int(price_jump.sum()),
}


# =============================================================================
# BUILD SUMMARY OUTPUT
# =============================================================================

section("BUILDING INTEGRITY SUMMARY")

summary_rows = []

for name, passed in validation.items():

    summary_rows.append(
        {
            "check": name,
            "status": "PASS" if passed else "FAIL",
            "value": int(passed),
        }
    )


summary_rows.extend(
    [
        {
            "check": "total_observations",
            "status": "INFO",
            "value": len(daily),
        },
        {
            "check": "total_securities",
            "status": "INFO",
            "value": daily["permno"].nunique(),
        },
        {
            "check": "crossed_quote_rows",
            "status": "DIAGNOSTIC",
            "value": crossed.sum(),
        },
        {
            "check": "return_outlier_rows",
            "status": "DIAGNOSTIC",
            "value": return_outlier.sum(),
        },
        {
            "check": "price_jump_rows",
            "status": "DIAGNOSTIC",
            "value": price_jump.sum(),
        },
        {
            "check": "zero_volume_rows",
            "status": "DIAGNOSTIC",
            "value": int(volume_zero),
        },
    ]
)

integrity_summary = pd.DataFrame(summary_rows)


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

section("SAVING OUTPUTS")

security_summary.to_csv(
    OUTPUT_SECURITY,
    index=False
)

integrity_summary.to_csv(
    OUTPUT_SUMMARY,
    index=False
)

print(f"Security summary:")
print(f"  {OUTPUT_SECURITY}")

print(f"Rows: {len(security_summary):,}")

print(f"\nIntegrity summary:")
print(f"  {OUTPUT_SUMMARY}")

print(f"Rows: {len(integrity_summary):,}")


# =============================================================================
# FINAL STATUS
# =============================================================================

section("DAILY INTEGRITY AUDIT COMPLETE")

if all(validation.values()):
    print(
        "PASS   Core daily data integrity checks passed."
    )
else:
    failed = [
        name
        for name, passed in validation.items()
        if not passed
    ]

    print(
        "FAIL   Core integrity checks require review:"
    )

    for name in failed:
        print(f"  - {name}")

print(
    "\nDiagnostic observations such as crossed quotes, "
    "return outliers, and large price jumps are retained "
    "for review and are not automatically removed."
)