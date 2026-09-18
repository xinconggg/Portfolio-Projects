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

OUTPUT_PANEL = (
    TIER2_DIR /
    "crsp_tier2_daily_panel.csv"
)

OUTPUT_SUMMARY = (
    TIER2_DIR /
    "crsp_tier2_daily_panel_summary.csv"
)

OUTPUT_COVERAGE = (
    TIER2_DIR /
    "crsp_tier2_daily_panel_coverage.csv"
)

OUTPUT_VALIDATION = (
    TIER2_DIR /
    "crsp_tier2_daily_panel_validation.csv"
)


# =============================================================================
# PARAMETERS
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")

# Valid Tier 2 historical classification.
VALID_PANEL_CLASSIFICATIONS = {
    "COMMON_EQUITY",
}


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


def parse_dates(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col],
                errors="coerce"
            )

    return df


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
master = normalize_permno(master)

required_master_columns = [
    "permno",
    "effective_start",
    "effective_end",
    "research_classification",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "issuertype",
    "usincflg",
    "primaryexch",
    "ticker",
]

missing_master_columns = [
    col
    for col in required_master_columns
    if col not in master.columns
]

if missing_master_columns:
    print("\nAvailable master columns:")
    print(master.columns.tolist())

    raise ValueError(
        "Required historical master columns missing: "
        + ", ".join(missing_master_columns)
    )


master = parse_dates(
    master,
    [
        "effective_start",
        "effective_end",
        "securitybegdt",
        "securityenddt",
    ],
)

master = master[
    master["permno"].notna()
].copy()

master_permnos = set(
    master["permno"].astype(int)
)

print(f"Master rows:      {len(master):,}")
print(f"Master PERMNOs:    {len(master_permnos):,}")


# =============================================================================
# LOAD ELIGIBLE UNIVERSE
# =============================================================================

print("\n" + "=" * 80)
print("LOADING TIER 2 ELIGIBLE UNIVERSE")
print("=" * 80)

eligible = pd.read_csv(
    ELIGIBLE_FILE,
    low_memory=False
)

eligible = normalize_columns(eligible)
eligible = normalize_permno(eligible)

if "permno" not in eligible.columns:
    raise ValueError(
        "Eligible universe does not contain PERMNO."
    )

eligible_permnos = set(
    eligible["permno"]
    .dropna()
    .astype(int)
)

print(f"Eligible rows:     {len(eligible):,}")
print(f"Eligible PERMNOs:   {len(eligible_permnos):,}")


# =============================================================================
# VERIFY ELIGIBLE UNIVERSE IS A SUBSET OF MASTER
# =============================================================================

eligible_not_in_master = (
    eligible_permnos -
    master_permnos
)

print("\n" + "=" * 80)
print("ELIGIBLE / MASTER RECONCILIATION")
print("=" * 80)

print(
    f"Eligible PERMNOs not in historical master: "
    f"{len(eligible_not_in_master):,}"
)

if eligible_not_in_master:
    print(sorted(eligible_not_in_master))

    raise ValueError(
        "CRITICAL: Eligible universe contains PERMNOs "
        "not present in historical security master."
    )


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
daily = normalize_permno(daily)

required_daily_columns = [
    "permno",
    "dlycaldt",
]

missing_daily_columns = [
    col
    for col in required_daily_columns
    if col not in daily.columns
]

if missing_daily_columns:
    print("\nAvailable Daily columns:")
    print(daily.columns.tolist())

    raise ValueError(
        "Required CRSP Daily columns missing: "
        + ", ".join(missing_daily_columns)
    )

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

daily = daily[
    daily["permno"].notna()
    & daily["dlycaldt"].notna()
].copy()

print(f"Daily rows:        {len(daily):,}")
print(f"Daily PERMNOs:     {daily['permno'].nunique():,}")
print(f"Daily first date:  {daily['dlycaldt'].min()}")
print(f"Daily last date:   {daily['dlycaldt'].max()}")


# =============================================================================
# RESEARCH WINDOW
# =============================================================================

daily = daily[
    daily["dlycaldt"].between(
        RESEARCH_START,
        RESEARCH_END,
        inclusive="both"
    )
].copy()

print("\n" + "=" * 80)
print("RESEARCH WINDOW")
print("=" * 80)

print(f"Research start:    {RESEARCH_START.date()}")
print(f"Research end:      {RESEARCH_END.date()}")
print(f"Daily rows:        {len(daily):,}")

if not daily.empty:
    print(
        f"Actual Daily range: "
        f"{daily['dlycaldt'].min().date()} -> "
        f"{daily['dlycaldt'].max().date()}"
    )


# =============================================================================
# DAILY KEY INTEGRITY
# =============================================================================

print("\n" + "=" * 80)
print("DAILY KEY INTEGRITY")
print("=" * 80)

duplicate_daily_keys = (
    daily
    .duplicated(
        ["permno", "dlycaldt"]
    )
    .sum()
)

print(
    f"Duplicate PERMNO-date observations: "
    f"{duplicate_daily_keys:,}"
)

if duplicate_daily_keys > 0:
    duplicates = daily[
        daily.duplicated(
            ["permno", "dlycaldt"],
            keep=False
        )
    ].sort_values(
        ["permno", "dlycaldt"]
    )

    print("\nDuplicate observations:")
    print(
        duplicates[
            ["permno", "dlycaldt"]
        ].head(50).to_string(index=False)
    )

    raise ValueError(
        "CRITICAL: Duplicate PERMNO-date observations detected."
    )


# =============================================================================
# RESTRICT DAILY TO ELIGIBLE HISTORICAL PERMNOS
# =============================================================================

daily_eligible = daily[
    daily["permno"].isin(eligible_permnos)
].copy()

daily_only_in_panel_input = (
    set(
        daily["permno"]
        .dropna()
        .astype(int)
    )
    -
    eligible_permnos
)

print("\n" + "=" * 80)
print("ELIGIBLE PERMNO FILTER")
print("=" * 80)

print(
    f"Daily rows before filter: "
    f"{len(daily):,}"
)

print(
    f"Daily rows after filter:  "
    f"{len(daily_eligible):,}"
)

print(
    f"Eligible PERMNOs represented: "
    f"{daily_eligible['permno'].nunique():,}"
)

print(
    f"Daily PERMNOs excluded from panel: "
    f"{len(daily_only_in_panel_input):,}"
)


# =============================================================================
# BUILD HISTORICAL MASTER INTERVALS
# =============================================================================
#
# Only eligible PERMNOs are relevant to the execution panel.
#
# We retain the actual effective interval boundaries.
#
# Research-window clipping is applied so that the master intervals cannot
# extend outside the research period.
# =============================================================================

print("\n" + "=" * 80)
print("BUILDING HISTORICAL MASTER INTERVALS")
print("=" * 80)

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
    [
        "permno",
        "panel_start",
    ]
)

print(
    f"Historical master interval rows: "
    f"{len(master_intervals):,}"
)

print(
    f"PERMNOs represented: "
    f"{master_intervals['permno'].nunique():,}"
)


# =============================================================================
# CHECK FOR OVERLAPPING MASTER INTERVALS
# =============================================================================

print("\n" + "=" * 80)
print("CHECKING HISTORICAL MASTER INTERVALS")
print("=" * 80)

master_intervals["previous_end"] = (
    master_intervals
    .groupby("permno")["panel_end"]
    .shift(1)
)

overlapping_intervals = master_intervals[
    master_intervals["previous_end"].notna()
    &
    (
        master_intervals["panel_start"]
        <=
        master_intervals["previous_end"]
    )
].copy()

print(
    f"Overlapping historical intervals: "
    f"{len(overlapping_intervals):,}"
)

if not overlapping_intervals.empty:

    print(
        overlapping_intervals[
            [
                "permno",
                "panel_start",
                "panel_end",
                "previous_end",
            ]
        ].to_string(index=False)
    )

    raise ValueError(
        "CRITICAL: Overlapping historical security-master "
        "intervals detected."
    )


# =============================================================================
# MATCH DAILY OBSERVATIONS TO HISTORICAL INTERVALS
# =============================================================================

print("\n" + "=" * 80)
print("MATCHING DAILY OBSERVATIONS TO HISTORICAL INTERVALS")
print("=" * 80)

matched_parts = []

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
    )

    master_group = master_group.sort_values(
        "panel_start"
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
                "ticker",
            ]
        ],
        left_on="dlycaldt",
        right_on="panel_start",
        by="permno",
        direction="backward",
        allow_exact_matches=True,
    )

    matched_parts.append(
        matched
    )


if matched_parts:

    matched_all = pd.concat(
        matched_parts,
        ignore_index=True
    )

else:

    matched_all = pd.DataFrame()


print(
    f"Daily observations processed: "
    f"{len(daily_eligible):,}"
)

print(
    f"Observations receiving a master interval: "
    f"{len(matched_all):,}"
)


# =============================================================================
# IDENTIFY UNMATCHED / OUTSIDE-INTERVAL OBSERVATIONS
# =============================================================================

if not matched_all.empty:

    unmatched_interval = (
        matched_all["panel_start"].isna()
        |
        matched_all["panel_end"].isna()
    )

    outside_interval = (
        ~unmatched_interval
        &
        (
            matched_all["dlycaldt"]
            <
            matched_all["panel_start"]
        )
        |
        (
            ~unmatched_interval
            &
            (
                matched_all["dlycaldt"]
                >
                matched_all["panel_end"]
            )
        )
    )

    matched_all["interval_match_valid"] = (
        ~unmatched_interval
        &
        ~outside_interval
    )

else:

    matched_all = pd.DataFrame()

    unmatched_interval = pd.Series(
        dtype=bool
    )

    outside_interval = pd.Series(
        dtype=bool
    )


invalid_interval_rows = (
    int((~matched_all["interval_match_valid"]).sum())
    if not matched_all.empty
    else 0
)

print(
    f"Daily observations outside valid historical interval: "
    f"{invalid_interval_rows:,}"
)


# =============================================================================
# FINAL PANEL
# =============================================================================

if not matched_all.empty:

    panel = matched_all[
        matched_all["interval_match_valid"]
    ].copy()

else:

    panel = pd.DataFrame()


if not panel.empty:

    panel = panel.sort_values(
        [
            "permno",
            "dlycaldt",
        ]
    ).reset_index(
        drop=True
    )


print("\n" + "=" * 80)
print("FINAL PANEL")
print("=" * 80)

print(
    f"Panel rows:       {len(panel):,}"
)

print(
    f"Panel PERMNOs:    "
    f"{panel['permno'].nunique() if not panel.empty else 0:,}"
)


# =============================================================================
# COVERAGE BY ELIGIBLE SECURITY
# =============================================================================

print("\n" + "=" * 80)
print("BUILDING ELIGIBLE SECURITY COVERAGE")
print("=" * 80)

eligible_meta_columns = [
    "permno",
    "ticker",
    "research_classification",
]

eligible_meta = (
    eligible[
        [
            col
            for col in eligible_meta_columns
            if col in eligible.columns
        ]
    ]
    .drop_duplicates("permno")
    .copy()
)

coverage = eligible_meta.copy()

if not panel.empty:

    daily_coverage = (
        panel
        .groupby("permno")
        .agg(
            daily_rows=("dlycaldt", "size"),
            daily_start=("dlycaldt", "min"),
            daily_end=("dlycaldt", "max"),
        )
        .reset_index()
    )

    coverage = coverage.merge(
        daily_coverage,
        on="permno",
        how="left"
    )

else:

    coverage["daily_rows"] = 0
    coverage["daily_start"] = pd.NaT
    coverage["daily_end"] = pd.NaT


coverage["daily_rows"] = (
    coverage["daily_rows"]
    .fillna(0)
    .astype(int)
)

coverage["has_daily_history"] = (
    coverage["daily_rows"] > 0
)

coverage["coverage_status"] = np.where(
    coverage["has_daily_history"],
    "HAS_DAILY_HISTORY",
    "NO_DAILY_HISTORY"
)


# =============================================================================
# FINAL CLASSIFICATION DIAGNOSTIC
# =============================================================================

print("\n" + "=" * 80)
print("FINAL PANEL CLASSIFICATION CHECK")
print("=" * 80)

if not panel.empty:

    print("\nPanel research classifications:")
    print(
        panel["research_classification"]
        .value_counts(dropna=False)
        .to_string()
    )

    invalid_classification_permnos = sorted(
        panel.loc[
            ~panel["research_classification"]
            .isin(VALID_PANEL_CLASSIFICATIONS),
            "permno"
        ]
        .dropna()
        .astype(int)
        .unique()
    )

    print("\nInvalid classification PERMNOs:")

    if invalid_classification_permnos:
        print(invalid_classification_permnos)
    else:
        print("None")

else:

    print("Panel is empty.")
    

# =============================================================================
# VALIDATION
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

validation = []


# -----------------------------------------------------------------------------
# 1. No ineligible PERMNOS
# -----------------------------------------------------------------------------

panel_permnos = set(
    panel["permno"]
    .dropna()
    .astype(int)
)

eligible_permnos = set(
    eligible["permno"]
    .dropna()
    .astype(int)
)

unexpected_panel_permnos = (
    panel_permnos - eligible_permnos
)

validation.append({
    "check": "panel_contains_only_eligible_permnos",
    "passed": len(unexpected_panel_permnos) == 0,
    "value": len(unexpected_panel_permnos),
})

# =============================================================================
# CLASSIFICATION DIAGNOSTIC
# =============================================================================

print("\n" + "=" * 80)
print("PANEL CLASSIFICATION DIAGNOSTIC")
print("=" * 80)

classification_cols = [
    col
    for col in [
        "research_classification",
        "securitytype",
        "securitysubtype",
        "sharetype",
        "issuertype",
        "usincflg",
    ]
    if col in panel.columns
]

for col in classification_cols:

    print(f"\n{col}:")

    print(
        panel[col]
        .value_counts(dropna=False)
        .head(20)
        .to_string()
    )


print("\nUnique panel PERMNOs:")
print(sorted(panel_permnos))

print("\nUnique eligible PERMNOs:")
print(sorted(eligible_permnos))

print("\nUnexpected panel PERMNOs:")
print(sorted(panel_permnos - eligible_permnos))

# -----------------------------------------------------------------------------
# 2. No duplicate PERMNO-date
# -----------------------------------------------------------------------------

if not panel.empty:

    panel_duplicates = (
        panel
        .duplicated(
            ["permno", "dlycaldt"]
        )
        .sum()
    )

else:

    panel_duplicates = 0

validation.append({
    "check": "no_duplicate_permno_date",
    "passed": panel_duplicates == 0,
    "value": int(panel_duplicates),
})


# -----------------------------------------------------------------------------
# 3. All dates within research window
# -----------------------------------------------------------------------------

if not panel.empty:

    outside_window = (
        ~panel["dlycaldt"].between(
            RESEARCH_START,
            RESEARCH_END,
            inclusive="both"
        )
    ).sum()

else:

    outside_window = 0

validation.append({
    "check": "all_dates_within_research_window",
    "passed": outside_window == 0,
    "value": int(outside_window),
})


# -----------------------------------------------------------------------------
# 4. Every panel row has an interval
# -----------------------------------------------------------------------------

if not panel.empty:

    missing_interval = (
        panel["panel_start"].isna()
        |
        panel["panel_end"].isna()
    ).sum()

else:

    missing_interval = 0

validation.append({
    "check": "all_rows_have_historical_interval",
    "passed": missing_interval == 0,
    "value": int(missing_interval),
})


# -----------------------------------------------------------------------------
# 5. Every date falls inside its historical interval
# -----------------------------------------------------------------------------

if not panel.empty:

    outside_interval = (
        (
            panel["dlycaldt"]
            <
            panel["panel_start"]
        )
        |
        (
            panel["dlycaldt"]
            >
            panel["panel_end"]
        )
    ).sum()

else:

    outside_interval = 0

validation.append({
    "check": "all_dates_within_historical_interval",
    "passed": outside_interval == 0,
    "value": int(outside_interval),
})


# -----------------------------------------------------------------------------
# 6. Only valid Tier 2 classification
# -----------------------------------------------------------------------------

if not panel.empty:

    invalid_classification = (
        ~panel["research_classification"]
        .isin(VALID_PANEL_CLASSIFICATIONS)
    ).sum()

else:

    invalid_classification = 0

validation.append({
    "check": "panel_contains_only_valid_tier2_classification",
    "passed": invalid_classification == 0,
    "value": int(invalid_classification),
})


# -----------------------------------------------------------------------------
# 7. Historical interval overlap check
# -----------------------------------------------------------------------------

validation.append({
    "check": "no_overlapping_master_intervals",
    "passed": len(overlapping_intervals) == 0,
    "value": int(len(overlapping_intervals)),
})


# -----------------------------------------------------------------------------
# 8. All eligible PERMNOS represented correctly
# -----------------------------------------------------------------------------

eligible_without_daily = (
    coverage["daily_rows"] == 0
).sum()

validation.append({
    "check": "eligible_coverage_accounted_for",
    "passed": (
        coverage["permno"].nunique()
        ==
        len(eligible_permnos)
    ),
    "value": int(
        coverage["permno"].nunique()
    ),
})


validation_df = pd.DataFrame(
    validation
)


# =============================================================================
# SUMMARY
# =============================================================================

summary = pd.DataFrame({
    "metric": [
        "historical_master_permnos",
        "eligible_permnos",
        "eligible_permnos_with_daily",
        "eligible_permnos_without_daily",
        "daily_panel_rows",
        "daily_panel_permnos",
        "daily_observations_outside_master_interval",
        "daily_permnos_outside_eligible_universe",
        "overlapping_master_intervals",
        "research_start",
        "research_end",
    ],

    "value": [
        len(master_permnos),
        len(eligible_permnos),
        int(
            (
                coverage["daily_rows"] > 0
            ).sum()
        ),
        int(
            (
                coverage["daily_rows"] == 0
            ).sum()
        ),
        len(panel),
        (
            panel["permno"].nunique()
            if not panel.empty
            else 0
        ),
        invalid_interval_rows,
        len(daily_only_in_panel_input),
        len(overlapping_intervals),
        RESEARCH_START.date(),
        RESEARCH_END.date(),
    ],
})


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("TIER 2 DAILY PANEL SUMMARY")
print("=" * 80)

print(
    summary.to_string(index=False)
)


print("\n" + "=" * 80)
print("COVERAGE STATUS")
print("=" * 80)

print(
    coverage["coverage_status"]
    .value_counts()
    .to_string()
)


print("\n" + "=" * 80)
print("VALIDATION RESULTS")
print("=" * 80)

print(
    validation_df.to_string(index=False)
)


# =============================================================================
# HARD FAIL
# =============================================================================

if not validation_df["passed"].all():

    print("\n" + "=" * 80)
    print("CRITICAL: VALIDATION FAILED")
    print("=" * 80)

    failed = validation_df[
        ~validation_df["passed"]
    ]

    print(
        failed.to_string(index=False)
    )

    raise ValueError(
        "Tier 2 Daily panel validation failed."
    )


# =============================================================================
# SAVE
# =============================================================================

panel.to_csv(
    OUTPUT_PANEL,
    index=False
)

summary.to_csv(
    OUTPUT_SUMMARY,
    index=False
)

coverage.to_csv(
    OUTPUT_COVERAGE,
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

print(f"Panel:       {OUTPUT_PANEL}")
print(f"Summary:     {OUTPUT_SUMMARY}")
print(f"Coverage:    {OUTPUT_COVERAGE}")
print(f"Validation:  {OUTPUT_VALIDATION}")

print("\nPASS: Tier 2 validated Daily panel successfully constructed.")