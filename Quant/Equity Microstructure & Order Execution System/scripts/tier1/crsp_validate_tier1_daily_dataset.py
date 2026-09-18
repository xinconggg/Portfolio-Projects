from pathlib import Path
import sys

import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"


DAILY_FILE = DATA_DIR / "crsp_tier1_daily.csv"
ELIGIBLE_FILE = DATA_DIR / "crsp_tier1_eligible_universe.csv"
SUMMARY_FILE = DATA_DIR / "crsp_tier1_daily_summary.csv"

OUTPUT_FILE = DATA_DIR / "crsp_tier1_daily_validation.csv"


RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPERS
# =============================================================================

def fail(message):
    print(f"FAIL   {message}")
    sys.exit(1)


def check(condition, passed_message, failed_message):
    if condition:
        print(f"PASS   {passed_message}")
        return True

    print(f"FAIL   {failed_message}")
    return False


# =============================================================================
# LOADING DATA
# =============================================================================

print("=" * 80)
print("LOADING TIER 1 DAILY DATASET")
print("=" * 80)

if not DAILY_FILE.exists():
    fail(f"Daily dataset not found: {DAILY_FILE}")

daily = pd.read_csv(DAILY_FILE, low_memory=False)

print(f"Rows loaded:        {len(daily):,}")
print(f"Columns loaded:     {len(daily.columns)}")


print()
print("=" * 80)
print("LOADING ELIGIBLE TIER 1 UNIVERSE")
print("=" * 80)

if not ELIGIBLE_FILE.exists():
    fail(f"Eligible universe not found: {ELIGIBLE_FILE}")

eligible = pd.read_csv(ELIGIBLE_FILE, low_memory=False)

print(f"Rows loaded:        {len(eligible):,}")


# =============================================================================
# NORMALIZING COLUMN NAMES
# =============================================================================

print()
print("=" * 80)
print("NORMALIZING COLUMN NAMES")
print("=" * 80)

daily.columns = daily.columns.str.strip().str.lower()
eligible.columns = eligible.columns.str.strip().str.lower()

print("PASS   Column names standardized to lowercase.")


# =============================================================================
# REQUIRED COLUMN VALIDATION
# =============================================================================

print()
print("=" * 80)
print("VALIDATING REQUIRED COLUMNS")
print("=" * 80)

required_daily_columns = {
    "permno",
    "permco",
    "dlycaldt",
    "dlyprc",
    "dlyret",
    "dlyretx",
    "dlyvol",
    "dlybid",
    "dlyask",
    "dlyopen",
    "dlyhigh",
    "dlylow",
    "dlyclose",
}

missing_daily_columns = sorted(
    required_daily_columns - set(daily.columns)
)

if missing_daily_columns:
    fail(
        "Missing required daily columns: "
        + ", ".join(missing_daily_columns)
    )

print("PASS   Required daily columns present.")


if "permno" not in eligible.columns:
    fail("Eligible universe is missing permno.")

print("PASS   Eligible universe contains permno.")


# =============================================================================
# NORMALIZING IDENTIFIERS
# =============================================================================

print()
print("=" * 80)
print("NORMALIZING IDENTIFIERS")
print("=" * 80)

daily["permno"] = pd.to_numeric(
    daily["permno"],
    errors="coerce"
).astype("Int64")

eligible["permno"] = pd.to_numeric(
    eligible["permno"],
    errors="coerce"
).astype("Int64")

print("PASS   PERMNO identifiers normalized.")


# =============================================================================
# PREPARING DATES
# =============================================================================

print()
print("=" * 80)
print("PREPARING DAILY DATES")
print("=" * 80)

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

invalid_dates = daily["dlycaldt"].isna().sum()

print(f"Invalid DlyCalDt values: {invalid_dates}")

if invalid_dates != 0:
    fail("Daily dataset contains invalid trading dates.")

print(
    f"Daily date range: "
    f"{daily['dlycaldt'].min().date()} to "
    f"{daily['dlycaldt'].max().date()}"
)


# =============================================================================
# BASIC STRUCTURAL VALIDATION
# =============================================================================

print()
print("=" * 80)
print("BASIC STRUCTURAL VALIDATION")
print("=" * 80)

duplicate_rows = daily.duplicated().sum()

duplicate_permno_date = daily.duplicated(
    subset=["permno", "dlycaldt"]
).sum()

missing_permno = daily["permno"].isna().sum()

print(f"Duplicate complete rows:       {duplicate_rows:,}")
print(f"Duplicate PERMNO-date rows:    {duplicate_permno_date:,}")
print(f"Missing PERMNO values:          {missing_permno:,}")

if duplicate_rows != 0:
    fail("Duplicate complete rows detected.")

if duplicate_permno_date != 0:
    fail("Duplicate PERMNO-date observations detected.")

if missing_permno != 0:
    fail("Missing PERMNO values detected.")

print("PASS   Structural validation passed.")


# =============================================================================
# PERMNO COVERAGE VALIDATION
# =============================================================================

print()
print("=" * 80)
print("VALIDATING PERMNO COVERAGE")
print("=" * 80)

eligible_permnos = set(
    eligible["permno"].dropna().astype(int)
)

daily_permnos = set(
    daily["permno"].dropna().astype(int)
)

missing_from_daily = sorted(
    eligible_permnos - daily_permnos
)

unexpected_in_daily = sorted(
    daily_permnos - eligible_permnos
)

print(f"Eligible PERMNOs:              {len(eligible_permnos)}")
print(f"Daily PERMNOs:                 {len(daily_permnos)}")
print(f"Missing from daily dataset:   {len(missing_from_daily)}")
print(f"Unexpected daily PERMNOs:     {len(unexpected_in_daily)}")

if missing_from_daily:
    print("Missing PERMNOs:", missing_from_daily)
    fail("Eligible PERMNOs are missing from daily dataset.")

if unexpected_in_daily:
    print("Unexpected PERMNOs:", unexpected_in_daily)
    fail("Unexpected PERMNOs found in daily dataset.")

print("PASS   PERMNO coverage exactly matches eligible universe.")


# =============================================================================
# RESEARCH WINDOW VALIDATION
# =============================================================================

print()
print("=" * 80)
print("VALIDATING RESEARCH WINDOW")
print("=" * 80)

outside_window = (
    (daily["dlycaldt"] < RESEARCH_START)
    | (daily["dlycaldt"] > RESEARCH_END)
).sum()

print(f"Research start:               {RESEARCH_START.date()}")
print(f"Research end:                 {RESEARCH_END.date()}")
print(f"Observations outside window:  {outside_window:,}")

if outside_window != 0:
    fail("Daily observations fall outside the research window.")

print("PASS   All observations lie within research window.")


# =============================================================================
# DATE ORDER VALIDATION
# =============================================================================

print()
print("=" * 80)
print("VALIDATING DATE ORDER")
print("=" * 80)

daily_sorted = daily.sort_values(
    ["permno", "dlycaldt"]
)

is_sorted = daily[
    ["permno", "dlycaldt"]
].reset_index(drop=True).equals(
    daily_sorted[
        ["permno", "dlycaldt"]
    ].reset_index(drop=True)
)

if not is_sorted:
    fail("Daily dataset is not sorted by PERMNO and date.")

print("PASS   Daily dataset sorted by PERMNO and date.")


# =============================================================================
# PERMCO CONSISTENCY
# =============================================================================

print()
print("=" * 80)
print("VALIDATING PERMCO CONSISTENCY")
print("=" * 80)

permco_counts = (
    daily.groupby("permno")["permco"]
    .nunique(dropna=True)
)

permnos_multiple_permco = (
    permco_counts[permco_counts > 1]
)

print(
    "PERMNOs with multiple PERMCOs: "
    f"{len(permnos_multiple_permco)}"
)

if len(permnos_multiple_permco) != 0:
    print(permnos_multiple_permco)
    fail("PERMNOs map to multiple PERMCOs in daily dataset.")

print("PASS   Each PERMNO maps to one PERMCO.")


# =============================================================================
# SECURITY TYPE VALIDATION
# =============================================================================

print()
print("=" * 80)
print("VALIDATING SECURITY TYPES")
print("=" * 80)

if "securitytype" in daily.columns:
    print()
    print(daily["securitytype"].value_counts(dropna=False))

    fund_rows = (
        daily["securitytype"]
        .astype("string")
        .str.upper()
        .eq("FUND")
        .sum()
    )
else:
    fund_rows = 0
    print("securitytype column not available.")

if "securitysubtype" in daily.columns:
    etf_rows = (
        daily["securitysubtype"]
        .astype("string")
        .str.upper()
        .eq("ETF")
        .sum()
    )
else:
    etf_rows = 0

print()
print(f"FUND rows:                    {fund_rows:,}")
print(f"ETF rows:                     {etf_rows:,}")

if fund_rows != 0 or etf_rows != 0:
    fail("FUND/ETF observations remain in Tier 1 daily dataset.")

print("PASS   No FUND/ETF observations remain.")


# =============================================================================
# PRICE / QUOTE FIELD SANITY CHECK
# =============================================================================

print()
print("=" * 80)
print("VALIDATING PRICE AND QUOTE FIELDS")
print("=" * 80)

numeric_columns = [
    "dlyprc",
    "dlyvol",
    "dlybid",
    "dlyask",
    "dlyopen",
    "dlyhigh",
    "dlylow",
    "dlyclose",
]

numeric_results = {}

for column in numeric_columns:

    if column not in daily.columns:
        continue

    values = pd.to_numeric(
        daily[column],
        errors="coerce"
    )

    negative_count = (values < 0).sum()

    numeric_results[column] = negative_count

    print(
        f"{column:12s} negative observations: "
        f"{negative_count:,}"
    )

    if negative_count != 0:
        fail(
            f"Negative values detected in {column}."
        )

print("PASS   No negative values detected in core numeric fields.")


# =============================================================================
# QUOTE CONSISTENCY
# =============================================================================
# =============================================================================
# QUOTE CONSISTENCY
# =============================================================================

print()
print("=" * 80)
print("CHECKING BID / ASK CONSISTENCY")
print("=" * 80)

invalid_quotes = 0
bid_only_count = 0
ask_only_count = 0
both_quotes_count = 0

if "dlybid" in daily.columns and "dlyask" in daily.columns:

    bid = pd.to_numeric(
        daily["dlybid"],
        errors="coerce"
    )

    ask = pd.to_numeric(
        daily["dlyask"],
        errors="coerce"
    )

    bid_present = bid.notna()
    ask_present = ask.notna()

    both_quotes = bid_present & ask_present
    bid_only = bid_present & ~ask_present
    ask_only = ~bid_present & ask_present

    invalid_quote_mask = (
        both_quotes
        & (bid > ask)
    )

    invalid_quotes = invalid_quote_mask.sum()
    bid_only_count = bid_only.sum()
    ask_only_count = ask_only.sum()
    both_quotes_count = both_quotes.sum()

    print(
        f"Observations with both bid and ask: "
        f"{both_quotes_count:,}"
    )

    print(
        f"Observations with bid only:          "
        f"{bid_only_count:,}"
    )

    print(
        f"Observations with ask only:          "
        f"{ask_only_count:,}"
    )

    print(
        f"Observations with bid > ask:         "
        f"{invalid_quotes:,}"
    )

    if invalid_quotes > 0:

        crossed_by_permno = (
            daily.loc[invalid_quote_mask]
            .groupby("permno")
            .size()
            .sort_values(ascending=False)
        )

        print()
        print("PERMNOs containing bid > ask observations:")
        print(crossed_by_permno.to_string())

        print()
        print(
            "WARNING  Crossed bid/ask observations detected."
        )
        print(
            "WARNING  Underlying CRSP values will be retained."
        )
        print(
            "WARNING  Quote consistency is treated as a diagnostic "
            "rather than a universe exclusion criterion."
        )

    else:
        print("PASS   No bid > ask observations detected.")

else:

    print(
        "WARNING  Bid/ask fields are not available; "
        "quote consistency was not evaluated."
    )


# =============================================================================
# DAILY OBSERVATION COUNTS
# =============================================================================

print()
print("=" * 80)
print("BUILDING SECURITY-LEVEL OBSERVATION COUNTS")
print("=" * 80)

security_summary = (
    daily.groupby("permno")
    .agg(
        daily_first_date=("dlycaldt", "min"),
        daily_last_date=("dlycaldt", "max"),
        daily_observations=("dlycaldt", "size"),
        daily_trading_days=("dlycaldt", "nunique"),
    )
    .reset_index()
)

print(
    f"Security-level summary rows: "
    f"{len(security_summary)}"
)


# =============================================================================
# CHECK FOR EMPTY SECURITY HISTORIES
# =============================================================================

print()
print("=" * 80)
print("VALIDATING SECURITY HISTORIES")
print("=" * 80)

zero_observation = (
    security_summary["daily_observations"] <= 0
).sum()

missing_security_summary = (
    len(eligible_permnos)
    - len(security_summary)
)

print(
    f"Securities with zero observations: "
    f"{zero_observation}"
)

print(
    f"Eligible securities missing summary: "
    f"{missing_security_summary}"
)

if zero_observation != 0:
    fail("Security with zero daily observations detected.")

if missing_security_summary != 0:
    fail("Eligible security missing from security-level summary.")

print("PASS   All eligible securities have daily observations.")


# =============================================================================
# CHECK FIRST / LAST DATES
# =============================================================================

print()
print("=" * 80)
print("VALIDATING SECURITY DATE BOUNDARIES")
print("=" * 80)

invalid_first_dates = (
    security_summary["daily_first_date"] < RESEARCH_START
).sum()

invalid_last_dates = (
    security_summary["daily_last_date"] > RESEARCH_END
).sum()

print(
    f"Histories beginning before research start: "
    f"{invalid_first_dates}"
)

print(
    f"Histories ending after research end: "
    f"{invalid_last_dates}"
)

if invalid_first_dates != 0:
    fail("Security history begins before research start.")

if invalid_last_dates != 0:
    fail("Security history extends beyond research end.")

print("PASS   Security date boundaries are valid.")


# =============================================================================
# COMPARING WITH ELIGIBLE UNIVERSE
# =============================================================================

print()
print("=" * 80)
print("CROSS-CHECKING ELIGIBLE UNIVERSE")
print("=" * 80)

eligible_subset = eligible[
    ["permno", "permco"]
].copy()

eligible_subset["permno"] = pd.to_numeric(
    eligible_subset["permno"],
    errors="coerce"
).astype("Int64")

eligible_subset["permco"] = pd.to_numeric(
    eligible_subset["permco"],
    errors="coerce"
).astype("Int64")

daily_permco = (
    daily.groupby("permno")["permco"]
    .first()
    .reset_index()
)

merged = eligible_subset.merge(
    daily_permco,
    on="permno",
    how="left",
    suffixes=("_eligible", "_daily")
)

permco_mismatch = (
    merged["permco_eligible"].notna()
    & merged["permco_daily"].notna()
    & (
        merged["permco_eligible"]
        != merged["permco_daily"]
    )
).sum()

print(
    f"PERMCO mismatches: {permco_mismatch}"
)

if permco_mismatch != 0:
    fail("PERMCO mismatch between eligible universe and daily dataset.")

print("PASS   PERMCO mappings agree with eligible universe.")


# =============================================================================
# BUILD VALIDATION SUMMARY
# =============================================================================

print()
print("=" * 80)
print("BUILDING FINAL VALIDATION SUMMARY")
print("=" * 80)

validation_rows = [
    {
        "check": "row_count_positive",
        "status": len(daily) > 0,
        "value": len(daily),
    },
    {
        "check": "unique_permnos_match",
        "status": len(daily_permnos) == len(eligible_permnos),
        "value": len(daily_permnos),
    },
    {
        "check": "no_duplicate_permno_date",
        "status": duplicate_permno_date == 0,
        "value": duplicate_permno_date,
    },
    {
        "check": "no_missing_permno",
        "status": missing_permno == 0,
        "value": missing_permno,
    },
    {
        "check": "no_fund_etf",
        "status": fund_rows == 0 and etf_rows == 0,
        "value": fund_rows + etf_rows,
    },
    {
        "check": "all_within_window",
        "status": outside_window == 0,
        "value": outside_window,
    },
    {
        "check": "all_eligible_present",
        "status": len(missing_from_daily) == 0,
        "value": len(missing_from_daily),
    },
    {
        "check": "no_unexpected_permnos",
        "status": len(unexpected_in_daily) == 0,
        "value": len(unexpected_in_daily),
    },
    {
        "check": "permco_consistency",
        "status": len(permnos_multiple_permco) == 0,
        "value": len(permnos_multiple_permco),
    },
    {
        "check": "bid_ask_consistency_diagnostic",
        "status": True,
        "value": (
            invalid_quotes
            if "invalid_quotes" in locals()
            else 0
        ),
    },
    {
        "check": "security_histories_complete",
        "status": (
            zero_observation == 0
            and missing_security_summary == 0
        ),
        "value": zero_observation + missing_security_summary,
    },
    {
        "check": "permco_matches_eligible",
        "status": permco_mismatch == 0,
        "value": permco_mismatch,
    },
]

validation_summary = pd.DataFrame(validation_rows)

print()
for _, row in validation_summary.iterrows():

    status_text = "PASS" if row["status"] else "FAIL"

    print(
        f"{status_text:5s} "
        f"{row['check']}"
    )


# =============================================================================
# FINAL STATUS
# =============================================================================

print()
print("=" * 80)
print("FINAL VALIDATION STATUS")
print("=" * 80)

all_passed = validation_summary["status"].all()

if all_passed:
    print("PASS   Tier 1 daily dataset passed all validation checks.")
else:
    print("FAIL   One or more Tier 1 daily validation checks failed.")


# =============================================================================
# SAVING VALIDATION SUMMARY
# =============================================================================

print()
print("=" * 80)
print("SAVING VALIDATION SUMMARY")
print("=" * 80)

validation_summary.to_csv(
    OUTPUT_FILE,
    index=False
)

print(f"Saved: {OUTPUT_FILE}")


# =============================================================================
# EXIT STATUS
# =============================================================================

if not all_passed:
    sys.exit(1)