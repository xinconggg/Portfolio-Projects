from pathlib import Path
import pandas as pd
import numpy as np


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

ELIGIBLE_FILE = (
    TIER2_DIR /
    "crsp_tier2_eligible_universe.csv"
)

DAILY_FILE = (
    DATA_DIR /
    "crsp_daily_clean.csv"
)

PANEL_FILE = (
    TIER2_DIR /
    "crsp_tier2_daily_panel.csv"
)

OUTPUT_REJECTIONS = (
    TIER2_DIR /
    "crsp_tier2_daily_panel_rejection_audit.csv"
)

OUTPUT_SUMMARY = (
    TIER2_DIR /
    "crsp_tier2_daily_panel_rejection_summary.csv"
)

OUTPUT_PERMNO_SUMMARY = (
    TIER2_DIR /
    "crsp_tier2_daily_panel_rejection_permno_summary.csv"
)

OUTPUT_VALIDATION = (
    TIER2_DIR /
    "crsp_tier2_daily_panel_rejection_validation.csv"
)


# =============================================================================
# PARAMETERS
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPERS
# =============================================================================

def normalize_columns(df):
    df.columns = [
        str(col).strip().lower()
        for col in df.columns
    ]
    return df


def normalize_permno(df):
    df["permno"] = pd.to_numeric(
        df["permno"],
        errors="coerce"
    ).astype("Int64")

    return df


# =============================================================================
# LOAD MASTER
# =============================================================================

print("=" * 80)
print("LOADING HISTORICAL SECURITY MASTER")
print("=" * 80)

master = pd.read_csv(
    MASTER_FILE,
    low_memory=False
)

master = normalize_columns(master)
master = normalize_permno(master)

for col in [
    "effective_start",
    "effective_end",
]:
    master[col] = pd.to_datetime(
        master[col],
        errors="coerce"
    )

master = master[
    master["permno"].notna()
].copy()

print(f"Master rows:       {len(master):,}")
print(f"Master PERMNOs:    {master['permno'].nunique():,}")


# =============================================================================
# LOAD ELIGIBLE UNIVERSE
# =============================================================================

print("\n" + "=" * 80)
print("LOADING ELIGIBLE UNIVERSE")
print("=" * 80)

eligible = pd.read_csv(
    ELIGIBLE_FILE,
    low_memory=False
)

eligible = normalize_columns(eligible)
eligible = normalize_permno(eligible)

eligible_permnos = set(
    eligible["permno"]
    .dropna()
    .astype(int)
)

print(f"Eligible PERMNOs:  {len(eligible_permnos):,}")


# =============================================================================
# LOAD DAILY
# =============================================================================

print("\n" + "=" * 80)
print("LOADING CRSP DAILY")
print("=" * 80)

daily = pd.read_csv(
    DAILY_FILE,
    low_memory=False
)

daily = normalize_columns(daily)
daily = normalize_permno(daily)

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

daily = daily[
    daily["permno"].notna()
    &
    daily["dlycaldt"].notna()
].copy()

daily = daily[
    daily["dlycaldt"].between(
        RESEARCH_START,
        RESEARCH_END,
        inclusive="both"
    )
].copy()

print(f"Research-window Daily rows: {len(daily):,}")


# =============================================================================
# RESTRICT TO ELIGIBLE PERMNOS
# =============================================================================

daily_eligible = daily[
    daily["permno"].isin(eligible_permnos)
].copy()

print(
    f"Eligible Daily observations: "
    f"{len(daily_eligible):,}"
)


# =============================================================================
# BUILD HISTORICAL INTERVALS
# =============================================================================

master_intervals = master[
    master["permno"].isin(eligible_permnos)
].copy()

master_intervals = master_intervals[
    master_intervals["effective_start"].notna()
    &
    master_intervals["effective_end"].notna()
].copy()

master_intervals["panel_start"] = (
    master_intervals["effective_start"]
    .clip(lower=RESEARCH_START)
)

master_intervals["panel_end"] = (
    master_intervals["effective_end"]
    .clip(upper=RESEARCH_END)
)

master_intervals = master_intervals[
    master_intervals["panel_start"]
    <=
    master_intervals["panel_end"]
].copy()

master_intervals = master_intervals.sort_values(
    ["permno", "panel_start"]
)


# =============================================================================
# MATCH DAILY TO HISTORICAL INTERVAL
# =============================================================================

print("\n" + "=" * 80)
print("MATCHING DAILY OBSERVATIONS TO HISTORICAL INTERVALS")
print("=" * 80)

parts = []

for permno, daily_group in daily_eligible.groupby(
    "permno",
    sort=True
):

    master_group = master_intervals[
        master_intervals["permno"] == permno
    ].copy()

    if master_group.empty:
        continue

    daily_group = daily_group.sort_values(
        "dlycaldt"
    ).copy()

    master_group = master_group.sort_values(
        "panel_start"
    ).copy()

    # -------------------------------------------------------------------------
    # Avoid column collisions between daily CRSP and historical master.
    #
    # The historical master is authoritative for historical classification
    # metadata, including ticker.
    # -------------------------------------------------------------------------

    master_group = master_group.rename(
        columns={
            "ticker": "historical_ticker"
        }
    )

    matched = pd.merge_asof(
        daily_group,
        master_group[
            [
                "permno",
                "panel_start",
                "panel_end",
                "research_classification",
                "securitytype",
                "securitysubtype",
                "sharetype",
                "issuertype",
                "usincflg",
                "primaryexch",
                "historical_ticker",
            ]
        ],
        left_on="dlycaldt",
        right_on="panel_start",
        by="permno",
        direction="backward",
        allow_exact_matches=True,
    )

    parts.append(matched)


if parts:

    matched = pd.concat(
        parts,
        ignore_index=True
    )

else:

    matched = pd.DataFrame()


# =============================================================================
# STANDARDIZE HISTORICAL TICKER
# =============================================================================

if "historical_ticker" in matched.columns:

    matched["ticker"] = matched["historical_ticker"]

else:

    matched["ticker"] = pd.NA

# =============================================================================
# CLASSIFY REJECTIONS
# =============================================================================

if matched.empty:
    raise ValueError(
        "No matched observations were produced."
    )


matched["rejection_reason"] = "VALID_PANEL_OBSERVATION"

missing_master_interval = (
    matched["panel_start"].isna()
    |
    matched["panel_end"].isna()
)

before_interval = (
    ~missing_master_interval
    &
    (
        matched["dlycaldt"]
        <
        matched["panel_start"]
    )
)

after_interval = (
    ~missing_master_interval
    &
    (
        matched["dlycaldt"]
        >
        matched["panel_end"]
    )
)

matched.loc[
    missing_master_interval,
    "rejection_reason"
] = "NO_HISTORICAL_INTERVAL"

matched.loc[
    before_interval,
    "rejection_reason"
] = "DAILY_BEFORE_HISTORICAL_INTERVAL"

matched.loc[
    after_interval,
    "rejection_reason"
] = "DAILY_AFTER_HISTORICAL_INTERVAL"


# =============================================================================
# ADD DURATION DIAGNOSTICS
# =============================================================================

matched["days_from_interval_start"] = (
    matched["dlycaldt"]
    -
    matched["panel_start"]
).dt.days

matched["days_after_interval_end"] = (
    matched["dlycaldt"]
    -
    matched["panel_end"]
).dt.days


# =============================================================================
# REJECTION DATASET
# =============================================================================

rejections = matched[
    matched["rejection_reason"]
    !=
    "VALID_PANEL_OBSERVATION"
].copy()

print("\n" + "=" * 80)
print("REJECTION AUDIT")
print("=" * 80)

print(
    f"Total matched observations: "
    f"{len(matched):,}"
)

print(
    f"Rejected observations:      "
    f"{len(rejections):,}"
)

print("\nRejection reasons:")

print(
    rejections["rejection_reason"]
    .value_counts(dropna=False)
    .to_string()
)


# =============================================================================
# PERMNO SUMMARY
# =============================================================================

permno_summary = (
    matched
    .groupby(
        [
            "permno",
            "ticker",
            "research_classification",
        ],
        dropna=False
    )
    .agg(
        total_daily_rows=("dlycaldt", "size"),
        valid_panel_rows=(
            "rejection_reason",
            lambda x: (
                x == "VALID_PANEL_OBSERVATION"
            ).sum()
        ),
        rejected_rows=(
            "rejection_reason",
            lambda x: (
                x != "VALID_PANEL_OBSERVATION"
            ).sum()
        ),
        daily_start=("dlycaldt", "min"),
        daily_end=("dlycaldt", "max"),
    )
    .reset_index()
)

permno_summary["rejection_rate"] = (
    permno_summary["rejected_rows"]
    /
    permno_summary["total_daily_rows"]
)


# =============================================================================
# GLOBAL SUMMARY
# =============================================================================

summary = pd.DataFrame({
    "metric": [
        "eligible_permnos",
        "eligible_daily_permnos",
        "daily_eligible_rows",
        "valid_panel_rows",
        "rejected_rows",
        "rejection_rate",
        "rejected_permnos",
        "research_start",
        "research_end",
    ],
    "value": [
        len(eligible_permnos),
        daily_eligible["permno"].nunique(),
        len(daily_eligible),
        int(
            (
                matched["rejection_reason"]
                ==
                "VALID_PANEL_OBSERVATION"
            ).sum()
        ),
        len(rejections),
        (
            len(rejections)
            /
            len(matched)
            if len(matched) > 0
            else np.nan
        ),
        rejections["permno"].nunique(),
        RESEARCH_START.date(),
        RESEARCH_END.date(),
    ],
})


# =============================================================================
# VALIDATION
# =============================================================================

validation = []

validation.append({
    "check": "all_rejections_have_reason",
    "passed": (
        rejections["rejection_reason"].notna().all()
    ),
    "value": int(
        rejections["rejection_reason"].isna().sum()
    ),
})

validation.append({
    "check": "valid_panel_rows_match_existing_panel",
    "passed": (
        int(
            (
                matched["rejection_reason"]
                ==
                "VALID_PANEL_OBSERVATION"
            ).sum()
        )
        ==
        len(
            pd.read_csv(
                PANEL_FILE,
                usecols=["permno", "dlycaldt"]
            )
        )
    ),
    "value": int(
        (
            matched["rejection_reason"]
            ==
            "VALID_PANEL_OBSERVATION"
        ).sum()
    ),
})

validation.append({
    "check": "all_rejections_are_outside_interval_or_unmatched",
    "passed": (
        rejections["rejection_reason"].isin([
            "NO_HISTORICAL_INTERVAL",
            "DAILY_BEFORE_HISTORICAL_INTERVAL",
            "DAILY_AFTER_HISTORICAL_INTERVAL",
        ]).all()
    ),
    "value": int(
        (
            ~rejections["rejection_reason"].isin([
                "NO_HISTORICAL_INTERVAL",
                "DAILY_BEFORE_HISTORICAL_INTERVAL",
                "DAILY_AFTER_HISTORICAL_INTERVAL",
            ])
        ).sum()
    ),
})


validation_df = pd.DataFrame(validation)


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("REJECTION SUMMARY")
print("=" * 80)

print(
    summary.to_string(index=False)
)

print("\n" + "=" * 80)
print("PERMNO REJECTION SUMMARY")
print("=" * 80)

print(
    permno_summary[
        [
            "permno",
            "ticker",
            "research_classification",
            "total_daily_rows",
            "valid_panel_rows",
            "rejected_rows",
            "rejection_rate",
            "daily_start",
            "daily_end",
        ]
    ]
    .sort_values(
        "rejected_rows",
        ascending=False
    )
    .to_string(index=False)
)

print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

print(
    validation_df.to_string(index=False)
)


# =============================================================================
# HARD FAIL
# =============================================================================

if not validation_df["passed"].all():

    raise ValueError(
        "Tier 2 panel rejection audit failed."
    )


# =============================================================================
# SAVE
# =============================================================================

rejections.to_csv(
    OUTPUT_REJECTIONS,
    index=False
)

summary.to_csv(
    OUTPUT_SUMMARY,
    index=False
)

permno_summary.to_csv(
    OUTPUT_PERMNO_SUMMARY,
    index=False
)

validation_df.to_csv(
    OUTPUT_VALIDATION,
    index=False
)


# =============================================================================
# FINAL
# =============================================================================

print("\n" + "=" * 80)
print("SAVED")
print("=" * 80)

print(f"Rejections:        {OUTPUT_REJECTIONS}")
print(f"Summary:           {OUTPUT_SUMMARY}")
print(f"PERMNO summary:    {OUTPUT_PERMNO_SUMMARY}")
print(f"Validation:        {OUTPUT_VALIDATION}")

print("\nPASS: Tier 2 panel rejection audit completed.")