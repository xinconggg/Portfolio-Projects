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

OUTPUT_FILE = DATA_DIR / "crsp_tier1_daily_quality_summary.csv"

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# LOADING DATA
# =============================================================================

print("=" * 80)
print("LOADING TIER 1 DAILY DATASET")
print("=" * 80)

if not DAILY_FILE.exists():
    print(f"ERROR   Daily dataset not found: {DAILY_FILE}")
    sys.exit(1)

daily = pd.read_csv(
    DAILY_FILE,
    low_memory=False
)

daily.columns = daily.columns.str.strip().str.lower()

print(f"Rows loaded:        {len(daily):,}")
print(f"Columns loaded:     {len(daily.columns)}")


print()
print("=" * 80)
print("LOADING ELIGIBLE TIER 1 UNIVERSE")
print("=" * 80)

if not ELIGIBLE_FILE.exists():
    print(f"ERROR   Eligible universe not found: {ELIGIBLE_FILE}")
    sys.exit(1)

eligible = pd.read_csv(
    ELIGIBLE_FILE,
    low_memory=False
)

eligible.columns = eligible.columns.str.strip().str.lower()

print(f"Eligible rows:      {len(eligible):,}")


# =============================================================================
# NORMALIZING IDENTIFIERS AND DATES
# =============================================================================

print()
print("=" * 80)
print("PREPARING DATA")
print("=" * 80)

daily["permno"] = pd.to_numeric(
    daily["permno"],
    errors="coerce"
).astype("Int64")

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

eligible["permno"] = pd.to_numeric(
    eligible["permno"],
    errors="coerce"
).astype("Int64")

print("PASS   Identifiers and dates prepared.")


# =============================================================================
# PREPARING NUMERIC FIELDS
# =============================================================================

numeric_columns = [
    "dlyprc",
    "dlyvol",
    "dlybid",
    "dlyask",
    "dlyopen",
    "dlyhigh",
    "dlylow",
    "dlyclose",
    "dlynumtrd",
    "dlyret",
    "dlyretx",
]

for column in numeric_columns:
    if column in daily.columns:
        daily[column] = pd.to_numeric(
            daily[column],
            errors="coerce"
        )


# =============================================================================
# BUILDING SECURITY-LEVEL QUALITY SUMMARY
# =============================================================================

print()
print("=" * 80)
print("BUILDING SECURITY-LEVEL QUALITY SUMMARY")
print("=" * 80)

records = []

for permno, group in daily.groupby("permno", sort=True):

    group = group.sort_values("dlycaldt")

    total_obs = len(group)

    first_date = group["dlycaldt"].min()
    last_date = group["dlycaldt"].max()

    trading_days = group["dlycaldt"].nunique()

    record = {
        "permno": int(permno),
        "daily_first_date": first_date,
        "daily_last_date": last_date,
        "daily_observations": total_obs,
        "daily_trading_days": trading_days,
    }

    # -------------------------------------------------------------------------
    # PRICE COVERAGE
    # -------------------------------------------------------------------------

    if "dlyprc" in group.columns:

        price_present = group["dlyprc"].notna()

        record["price_missing"] = (~price_present).sum()
        record["price_missing_pct"] = (
            (~price_present).mean() * 100
        )

    else:

        record["price_missing"] = pd.NA
        record["price_missing_pct"] = pd.NA


    # -------------------------------------------------------------------------
    # VOLUME COVERAGE
    # -------------------------------------------------------------------------

    if "dlyvol" in group.columns:

        volume_present = group["dlyvol"].notna()

        record["volume_missing"] = (~volume_present).sum()
        record["volume_missing_pct"] = (
            (~volume_present).mean() * 100
        )

        record["zero_volume"] = (
            group["dlyvol"] == 0
        ).sum()

    else:

        record["volume_missing"] = pd.NA
        record["volume_missing_pct"] = pd.NA
        record["zero_volume"] = pd.NA


    # -------------------------------------------------------------------------
    # BID / ASK COVERAGE
    # -------------------------------------------------------------------------

    if "dlybid" in group.columns:

        bid_present = group["dlybid"].notna()

        record["bid_missing"] = (~bid_present).sum()
        record["bid_missing_pct"] = (
            (~bid_present).mean() * 100
        )

    else:

        bid_present = pd.Series(
            False,
            index=group.index
        )

        record["bid_missing"] = pd.NA
        record["bid_missing_pct"] = pd.NA


    if "dlyask" in group.columns:

        ask_present = group["dlyask"].notna()

        record["ask_missing"] = (~ask_present).sum()
        record["ask_missing_pct"] = (
            (~ask_present).mean() * 100
        )

    else:

        ask_present = pd.Series(
            False,
            index=group.index
        )

        record["ask_missing"] = pd.NA
        record["ask_missing_pct"] = pd.NA


    # -------------------------------------------------------------------------
    # BOTH BID AND ASK
    # -------------------------------------------------------------------------

    if "dlybid" in group.columns and "dlyask" in group.columns:

        both_quotes = (
            group["dlybid"].notna()
            & group["dlyask"].notna()
        )

        crossed_quotes = (
            both_quotes
            & (group["dlybid"] > group["dlyask"])
        )

        record["both_bid_ask"] = both_quotes.sum()

        record["both_bid_ask_pct"] = (
            both_quotes.mean() * 100
        )

        record["crossed_bid_ask"] = crossed_quotes.sum()

        record["crossed_bid_ask_pct"] = (
            crossed_quotes.mean() * 100
        )

    else:

        record["both_bid_ask"] = pd.NA
        record["both_bid_ask_pct"] = pd.NA
        record["crossed_bid_ask"] = pd.NA
        record["crossed_bid_ask_pct"] = pd.NA


    # -------------------------------------------------------------------------
    # RETURN COVERAGE
    # -------------------------------------------------------------------------

    if "dlyret" in group.columns:

        ret_missing = group["dlyret"].isna()

        record["return_missing"] = ret_missing.sum()

        record["return_missing_pct"] = (
            ret_missing.mean() * 100
        )

    else:

        record["return_missing"] = pd.NA
        record["return_missing_pct"] = pd.NA


    # -------------------------------------------------------------------------
    # TRADE COUNT COVERAGE
    # -------------------------------------------------------------------------

    if "dlynumtrd" in group.columns:

        trade_count_missing = group["dlynumtrd"].isna()

        record["trade_count_missing"] = (
            trade_count_missing.sum()
        )

        record["trade_count_missing_pct"] = (
            trade_count_missing.mean() * 100
        )

    else:

        record["trade_count_missing"] = pd.NA
        record["trade_count_missing_pct"] = pd.NA


    records.append(record)


quality = pd.DataFrame(records)


# =============================================================================
# ATTACH ELIGIBLE UNIVERSE IDENTIFIERS
# =============================================================================

print()
print("=" * 80)
print("ATTACHING UNIVERSE IDENTIFIERS")
print("=" * 80)

universe_columns = [
    "permno",
    "permco",
    "ticker",
    "cusip",
    "primaryexch",
    "siccd",
    "securitybegdt",
    "securityenddt",
]

available_universe_columns = [
    column
    for column in universe_columns
    if column in eligible.columns
]

universe_info = eligible[
    available_universe_columns
].copy()

universe_info = universe_info.drop_duplicates(
    subset=["permno"]
)

quality = quality.merge(
    universe_info,
    on="permno",
    how="left"
)

print("PASS   Universe identifiers attached.")


# =============================================================================
# CALCULATING COVERAGE FLAGS
# =============================================================================

print()
print("=" * 80)
print("CALCULATING COVERAGE FLAGS")
print("=" * 80)

quality["full_price_coverage"] = (
    quality["price_missing"] == 0
)

quality["full_volume_coverage"] = (
    quality["volume_missing"] == 0
)

quality["full_quote_coverage"] = (
    (quality["bid_missing"] == 0)
    & (quality["ask_missing"] == 0)
)

quality["has_crossed_quotes"] = (
    quality["crossed_bid_ask"] > 0
)

quality["full_return_coverage"] = (
    quality["return_missing"] == 0
)

quality["full_trade_count_coverage"] = (
    quality["trade_count_missing"] == 0
)


# =============================================================================
# CALCULATING SECURITY AGE
# =============================================================================

print()
print("=" * 80)
print("CALCULATING SECURITY HISTORY LENGTH")
print("=" * 80)

quality["history_calendar_days"] = (
    quality["daily_last_date"]
    - quality["daily_first_date"]
).dt.days + 1

quality["history_years_approx"] = (
    quality["history_calendar_days"] / 365.25
)

print("PASS   History length calculated.")


# =============================================================================
# ORDERING OUTPUT
# =============================================================================

output_columns = [
    "permno",
    "permco",
    "ticker",
    "cusip",
    "primaryexch",
    "siccd",
    "daily_first_date",
    "daily_last_date",
    "daily_observations",
    "daily_trading_days",
    "history_calendar_days",
    "history_years_approx",

    "price_missing",
    "price_missing_pct",
    "volume_missing",
    "volume_missing_pct",
    "zero_volume",

    "bid_missing",
    "bid_missing_pct",
    "ask_missing",
    "ask_missing_pct",
    "both_bid_ask",
    "both_bid_ask_pct",
    "crossed_bid_ask",
    "crossed_bid_ask_pct",

    "return_missing",
    "return_missing_pct",

    "trade_count_missing",
    "trade_count_missing_pct",

    "full_price_coverage",
    "full_volume_coverage",
    "full_quote_coverage",
    "has_crossed_quotes",
    "full_return_coverage",
    "full_trade_count_coverage",
]

output_columns = [
    column
    for column in output_columns
    if column in quality.columns
]

quality = quality[
    output_columns
].sort_values("permno")


# =============================================================================
# FINAL VALIDATION
# =============================================================================

print()
print("=" * 80)
print("FINAL QUALITY SUMMARY VALIDATION")
print("=" * 80)

expected_permnos = set(
    eligible["permno"].dropna().astype(int)
)

summary_permnos = set(
    quality["permno"].dropna().astype(int)
)

missing_permnos = expected_permnos - summary_permnos
unexpected_permnos = summary_permnos - expected_permnos

print(
    f"Eligible securities:           "
    f"{len(expected_permnos)}"
)

print(
    f"Quality summary securities:    "
    f"{len(summary_permnos)}"
)

print(
    f"Missing securities:            "
    f"{len(missing_permnos)}"
)

print(
    f"Unexpected securities:         "
    f"{len(unexpected_permnos)}"
)

if missing_permnos:
    print("Missing:", sorted(missing_permnos))
    sys.exit(1)

if unexpected_permnos:
    print("Unexpected:", sorted(unexpected_permnos))
    sys.exit(1)

if quality["permno"].duplicated().any():
    print("ERROR   Duplicate PERMNOs in quality summary.")
    sys.exit(1)

print("PASS   Quality summary contains exactly one row per eligible PERMNO.")


# =============================================================================
# OVERALL QUALITY STATISTICS
# =============================================================================

print()
print("=" * 80)
print("OVERALL QUALITY STATISTICS")
print("=" * 80)

print(
    f"Total daily observations:      "
    f"{len(daily):,}"
)

print(
    f"Total securities:              "
    f"{quality['permno'].nunique()}"
)

print(
    f"Securities with crossed quotes:"
    f" {quality['has_crossed_quotes'].sum()}"
)

print(
    f"Total crossed quote rows:      "
    f"{quality['crossed_bid_ask'].sum():,}"
)

print(
    f"Securities with full price coverage:"
    f" {quality['full_price_coverage'].sum()}"
)

print(
    f"Securities with full volume coverage:"
    f" {quality['full_volume_coverage'].sum()}"
)

print(
    f"Securities with full quote coverage:"
    f" {quality['full_quote_coverage'].sum()}"
)

print(
    f"Securities with full return coverage:"
    f" {quality['full_return_coverage'].sum()}"
)


# =============================================================================
# SAVING OUTPUT
# =============================================================================

print()
print("=" * 80)
print("SAVING QUALITY SUMMARY")
print("=" * 80)

quality.to_csv(
    OUTPUT_FILE,
    index=False
)

print(f"Saved: {OUTPUT_FILE}")
print(f"Rows:  {len(quality)}")


# =============================================================================
# COMPLETION STATUS
# =============================================================================

print()
print("=" * 80)
print("QUALITY SUMMARY COMPLETE")
print("=" * 80)

print(
    f"Tier 1 securities documented: "
    f"{len(quality)}"
)

print(
    f"Daily observations documented: "
    f"{len(daily):,}"
)