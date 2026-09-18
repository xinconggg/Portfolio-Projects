from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TAQ_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "taq"
    / "taq.csv"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
)

TRADE_OUTPUT = (
    PROCESSED_DIR
    / "taq_trade_quality_summary.csv"
)

QUOTE_OUTPUT = (
    PROCESSED_DIR
    / "taq_quote_quality_summary.csv"
)

CONSISTENCY_OUTPUT = (
    PROCESSED_DIR
    / "taq_microstructure_consistency.csv"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

CHUNK_SIZE = 100_000


# =============================================================================
# EXPECTED FIELD GROUPS
# =============================================================================

QUOTE_PRICE_FIELDS = [
    "BB_1pm",
    "BO_1pm",
    "MID_1pm",
    "BB_c1",
    "BO_c1",
    "Mid_c1",
    "BB_4pm",
    "BO_4pm",
    "Mid_4pm",
    "LBB",
    "LBO",
    "LMid",
    "CPrc",
    "CPrc2",
]

TRADE_PRICE_FIELDS = [
    "OPrice",
    "DPrice",
    "LPrice",
    "Price_1pm",
    "Price_4pm",
]

TRADE_COUNT_FIELDS = [
    "NumTrades_t",
    "NumTrades_m",
    "NumISOTrades_m",
    "NumOddLotTrades_m",
    "NumMixedLotTrades_m",
]

VOLUME_FIELDS = [
    "SumVolume_t",
    "SumVolume_m",
    "SumISOVolume_m",
    "SumOddLotVolume_m",
    "SumMixedLotVolume_m",
    "BuyVol_LR1",
    "SellVol_LR1",
]

VALUE_FIELDS = [
    "SumValue_b",
    "SumValue_m",
    "SumISOValue_m",
    "SumOddLotValue_m",
    "SumMixedLotValue_m",
    "BuyDollar_LR1",
    "SellDollar_LR1",
]

EXECUTION_FIELDS = [
    "ESpreadDollar_Avg1",
    "ESpreadPct_Avg1",
    "RSpreadDollar_Avg1",
    "RSpreadPct_Avg1",
    "PriceImpactDollar_Avg1",
    "PriceImpactPct_Avg1",
    "ESpreadDollar_VW1",
    "ESpreadDollar_SW1",
    "ESpreadPct_VW1",
    "ESpreadPct_SW1",
    "RSpreadDollar_SW1",
    "RSpreadDollar_VW1",
    "RSpreadPct_SW1",
    "RSpreadPct_VW1",
    "PriceImpactDollar_VW1",
    "PriceImpactDollar_SW1",
    "PriceImpactPct_VW1",
    "PriceImpactPct_SW1",
]

TRADE_DIRECTION_FIELDS = [
    "BuyNumTrades_LR1",
    "SellNumTrades_LR1",
    "BuyVol_LR1",
    "SellVol_LR1",
    "BuyDollar_LR1",
    "SellDollar_LR1",
]

QUOTE_SPREAD_FIELDS = [
    "QSpreadDollar_EW_m",
    "QSpreadPct_EW_m",
    "QSpreadDollar_TW_m",
    "QSpreadPct_TW_m",
]

DEPTH_FIELDS = [
    "TOfrDollar_TW_m",
    "TBidDollar_TW_m",
    "TOfrShares_TW_m",
    "TBidShares_TW_m",
    "BOfrDollar_TW_m",
    "BBidDollar_TW_m",
    "BOfrShares_TW_m",
    "BBidShares_TW_m",
]


# =============================================================================
# HELPERS
# =============================================================================

def print_header(title):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def numeric(series):

    return pd.to_numeric(
        series,
        errors="coerce",
    )


def count_condition(series, condition):

    return int(
        condition.fillna(False).sum()
    )


def safe_ratio(
    numerator,
    denominator,
):

    denominator = denominator.replace(
        0,
        np.nan,
    )

    return numerator / denominator


def field_exists(
    df,
    field,
):

    return field in df.columns


def build_basic_quality_summary(
    df,
    fields,
):

    records = []

    for field in fields:

        if field not in df.columns:

            continue

        s = numeric(
            df[field]
        )

        finite = (
            s.replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .dropna()
        )

        records.append(
            {
                "field": field,
                "rows": len(df),
                "missing_count": int(
                    df[field].isna().sum()
                ),
                "missing_rate": (
                    df[field].isna().mean()
                ),
                "zero_count": int(
                    (s == 0).sum()
                ),
                "negative_count": int(
                    (s < 0).sum()
                ),
                "positive_count": int(
                    (s > 0).sum()
                ),
                "min": (
                    finite.min()
                    if not finite.empty
                    else np.nan
                ),
                "max": (
                    finite.max()
                    if not finite.empty
                    else np.nan
                ),
                "median": (
                    finite.median()
                    if not finite.empty
                    else np.nan
                ),
                "mean": (
                    finite.mean()
                    if not finite.empty
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(
        records
    )


# =============================================================================
# LOAD
# =============================================================================

def load_data():

    if not TAQ_FILE.exists():

        raise FileNotFoundError(
            f"TAQ source file not found:\n{TAQ_FILE}"
        )

    print_header(
        "LOADING TAQ DERIVED MICROSTRUCTURE DATA"
    )

    print(
        f"Source:\n{TAQ_FILE}"
    )

    df = pd.read_csv(
        TAQ_FILE,
        low_memory=False,
    )

    print(
        f"Rows loaded: {len(df):,}"
    )

    print(
        f"Columns loaded: {len(df.columns):,}"
    )

    return df


# =============================================================================
# TRADE QUALITY
# =============================================================================

def diagnose_trade_quality(df):

    print_header(
        "TRADE / TRADING-ACTIVITY QUALITY"
    )

    records = []

    # -------------------------------------------------------------------------
    # Basic field diagnostics
    # -------------------------------------------------------------------------

    basic_fields = (
        TRADE_PRICE_FIELDS
        + TRADE_COUNT_FIELDS
        + VOLUME_FIELDS
        + VALUE_FIELDS
        + TRADE_DIRECTION_FIELDS
    )

    basic = build_basic_quality_summary(
        df,
        basic_fields,
    )

    if not basic.empty:

        records.extend(
            basic.to_dict(
                orient="records"
            )
        )

    # -------------------------------------------------------------------------
    # Cross-field tests
    # -------------------------------------------------------------------------

    tests = []

    # NumTrades_t
    if {
        "NumTrades_t",
        "NumTrades_m",
    }.issubset(df.columns):

        a = numeric(
            df["NumTrades_t"]
        )

        b = numeric(
            df["NumTrades_m"]
        )

        tests.append(
            {
                "diagnostic": (
                    "NumTrades_t_vs_NumTrades_m"
                ),
                "test_type": (
                    "DIFFERENCE"
                ),
                "observations": len(df),
                "violations": int(
                    (
                        a.notna()
                        & b.notna()
                        & (a < 0)
                    ).sum()
                ),
                "description": (
                    "NumTrades_t should not be "
                    "negative."
                ),
            }
        )

    # -------------------------------------------------------------------------
    # Buy/Sell trade-count reconciliation
    # -------------------------------------------------------------------------

    if {
        "BuyNumTrades_LR1",
        "SellNumTrades_LR1",
        "NumTrades_t",
    }.issubset(df.columns):

        buy = numeric(
            df["BuyNumTrades_LR1"]
        )

        sell = numeric(
            df["SellNumTrades_LR1"]
        )

        total = numeric(
            df["NumTrades_t"]
        )

        calculated = (
            buy + sell
        )

        comparable = (
            calculated.notna()
            & total.notna()
        )

        violations = (
            comparable
            & ~np.isclose(
                calculated,
                total,
                rtol=1e-8,
                atol=1e-8,
            )
        )

        tests.append(
            {
                "diagnostic": (
                    "BuySellTradeCount_vs_Total"
                ),
                "test_type": (
                    "RECONCILIATION"
                ),
                "observations": int(
                    comparable.sum()
                ),
                "violations": int(
                    violations.sum()
                ),
                "description": (
                    "BuyNumTrades_LR1 + "
                    "SellNumTrades_LR1 "
                    "compared with NumTrades_t."
                ),
            }
        )

    # -------------------------------------------------------------------------
    # Buy/Sell volume reconciliation
    # -------------------------------------------------------------------------

    if {
        "BuyVol_LR1",
        "SellVol_LR1",
        "SumVolume_t",
    }.issubset(df.columns):

        buy = numeric(
            df["BuyVol_LR1"]
        )

        sell = numeric(
            df["SellVol_LR1"]
        )

        total = numeric(
            df["SumVolume_t"]
        )

        calculated = (
            buy + sell
        )

        comparable = (
            calculated.notna()
            & total.notna()
        )

        violations = (
            comparable
            & ~np.isclose(
                calculated,
                total,
                rtol=1e-8,
                atol=1e-8,
            )
        )

        tests.append(
            {
                "diagnostic": (
                    "BuySellVolume_vs_Total"
                ),
                "test_type": (
                    "RECONCILIATION"
                ),
                "observations": int(
                    comparable.sum()
                ),
                "violations": int(
                    violations.sum()
                ),
                "description": (
                    "BuyVol_LR1 + SellVol_LR1 "
                    "compared with SumVolume_t."
                ),
            }
        )

    # -------------------------------------------------------------------------
    # Buy/Sell dollar reconciliation
    # -------------------------------------------------------------------------

    if {
        "BuyDollar_LR1",
        "SellDollar_LR1",
        "SumValue_b",
    }.issubset(df.columns):

        buy = numeric(
            df["BuyDollar_LR1"]
        )

        sell = numeric(
            df["SellDollar_LR1"]
        )

        total = numeric(
            df["SumValue_b"]
        )

        calculated = (
            buy + sell
        )

        comparable = (
            calculated.notna()
            & total.notna()
        )

        violations = (
            comparable
            & ~np.isclose(
                calculated,
                total,
                rtol=1e-6,
                atol=1e-6,
            )
        )

        tests.append(
            {
                "diagnostic": (
                    "BuySellDollar_vs_Total"
                ),
                "test_type": (
                    "RECONCILIATION"
                ),
                "observations": int(
                    comparable.sum()
                ),
                "violations": int(
                    violations.sum()
                ),
                "description": (
                    "BuyDollar_LR1 + "
                    "SellDollar_LR1 "
                    "compared with SumValue_b."
                ),
            }
        )

    # -------------------------------------------------------------------------
    # Component trade counts
    # -------------------------------------------------------------------------

    component_fields = [
        "NumISOTrades_m",
        "NumOddLotTrades_m",
        "NumMixedLotTrades_m",
    ]

    if all(
        field in df.columns
        for field in component_fields
    ):

        components = sum(
            numeric(df[field])
            for field in component_fields
        )

        total = numeric(
            df["NumTrades_m"]
        )

        comparable = (
            components.notna()
            & total.notna()
        )

        exceeds = (
            comparable
            & (components > total)
        )

        tests.append(
            {
                "diagnostic": (
                    "TradeComponents_vs_Total"
                ),
                "test_type": (
                    "BOUND"
                ),
                "observations": int(
                    comparable.sum()
                ),
                "violations": int(
                    exceeds.sum()
                ),
                "description": (
                    "ISO + odd-lot + mixed-lot "
                    "trade counts should not "
                    "exceed total trades."
                ),
            }
        )

    # -------------------------------------------------------------------------
    # Component volumes
    # -------------------------------------------------------------------------

    component_volume_fields = [
        "SumISOVolume_m",
        "SumOddLotVolume_m",
        "SumMixedLotVolume_m",
    ]

    if all(
        field in df.columns
        for field in component_volume_fields
    ):

        components = sum(
            numeric(df[field])
            for field in component_volume_fields
        )

        total = numeric(
            df["SumVolume_m"]
        )

        comparable = (
            components.notna()
            & total.notna()
        )

        exceeds = (
            comparable
            & (components > total)
        )

        tests.append(
            {
                "diagnostic": (
                    "VolumeComponents_vs_Total"
                ),
                "test_type": (
                    "BOUND"
                ),
                "observations": int(
                    comparable.sum()
                ),
                "violations": int(
                    exceeds.sum()
                ),
                "description": (
                    "ISO + odd-lot + mixed-lot "
                    "volume should not exceed "
                    "total volume."
                ),
            }
        )

    # -------------------------------------------------------------------------
    # Non-negative count/volume/value checks
    # -------------------------------------------------------------------------

    nonnegative_fields = (
        TRADE_COUNT_FIELDS
        + VOLUME_FIELDS
        + VALUE_FIELDS
    )

    for field in nonnegative_fields:

        if field not in df.columns:
            continue

        s = numeric(
            df[field]
        )

        comparable = s.notna()

        violations = (
            comparable
            & (s < 0)
        )

        tests.append(
            {
                "diagnostic": (
                    f"{field}_nonnegative"
                ),
                "test_type": (
                    "VALIDITY"
                ),
                "observations": int(
                    comparable.sum()
                ),
                "violations": int(
                    violations.sum()
                ),
                "description": (
                    f"{field} should not "
                    "contain negative values."
                ),
            }
        )

    trade_quality_df = pd.DataFrame(
        records
    )

    consistency_df = pd.DataFrame(
        tests
    )

    return (
        trade_quality_df,
        consistency_df,
    )


# =============================================================================
# QUOTE QUALITY
# =============================================================================

def diagnose_quote_quality(df):

    print_header(
        "QUOTE QUALITY"
    )

    records = []

    # -------------------------------------------------------------------------
    # Basic quote field diagnostics
    # -------------------------------------------------------------------------

    basic = build_basic_quality_summary(
        df,
        QUOTE_PRICE_FIELDS,
    )

    if not basic.empty:

        records.extend(
            basic.to_dict(
                orient="records"
            )
        )

    # -------------------------------------------------------------------------
    # Quote relationship diagnostics
    # -------------------------------------------------------------------------

    tests = []

    quote_pairs = [
        (
            "BB_1pm",
            "MID_1pm",
            "BO_1pm",
            "1PM",
        ),
        (
            "BB_c1",
            "Mid_c1",
            "BO_c1",
            "C1",
        ),
        (
            "BB_4pm",
            "Mid_4pm",
            "BO_4pm",
            "4PM",
        ),
        (
            "LBB",
            "LMid",
            "LBO",
            "LAST",
        ),
    ]

    for bid_field, mid_field, ask_field, label in quote_pairs:

        if not all(
            field in df.columns
            for field in [
                bid_field,
                mid_field,
                ask_field,
            ]
        ):
            continue

        bid = numeric(
            df[bid_field]
        )

        mid = numeric(
            df[mid_field]
        )

        ask = numeric(
            df[ask_field]
        )

        comparable = (
            bid.notna()
            & mid.notna()
            & ask.notna()
        )

        bid_mid_violations = (
            comparable
            & (mid < bid)
        )

        mid_ask_violations = (
            comparable
            & (mid > ask)
        )

        bid_ask_violations = (
            comparable
            & (ask < bid)
        )

        tests.extend(
            [
                {
                    "diagnostic": (
                        f"{label}_MID_BELOW_BID"
                    ),
                    "test_type": (
                        "QUOTE_RELATIONSHIP"
                    ),
                    "observations": int(
                        comparable.sum()
                    ),
                    "violations": int(
                        bid_mid_violations.sum()
                    ),
                    "description": (
                        f"{mid_field} < "
                        f"{bid_field}."
                    ),
                },
                {
                    "diagnostic": (
                        f"{label}_MID_ABOVE_ASK"
                    ),
                    "test_type": (
                        "QUOTE_RELATIONSHIP"
                    ),
                    "observations": int(
                        comparable.sum()
                    ),
                    "violations": int(
                        mid_ask_violations.sum()
                    ),
                    "description": (
                        f"{mid_field} > "
                        f"{ask_field}."
                    ),
                },
                {
                    "diagnostic": (
                        f"{label}_CROSSED"
                    ),
                    "test_type": (
                        "QUOTE_RELATIONSHIP"
                    ),
                    "observations": int(
                        comparable.sum()
                    ),
                    "violations": int(
                        bid_ask_violations.sum()
                    ),
                    "description": (
                        f"{ask_field} < "
                        f"{bid_field}."
                    ),
                },
            ]
        )

        # Locked quotes
        locked = (
            comparable
            & np.isclose(
                bid,
                ask,
                rtol=1e-10,
                atol=1e-10,
            )
        )

        tests.append(
            {
                "diagnostic": (
                    f"{label}_LOCKED"
                ),
                "test_type": (
                    "QUOTE_STATE"
                ),
                "observations": int(
                    comparable.sum()
                ),
                "violations": int(
                    locked.sum()
                ),
                "description": (
                    "Bid equals ask."
                ),
            }
        )

    # -------------------------------------------------------------------------
    # Quote spread calculations
    # -------------------------------------------------------------------------

    spread_pairs = [
        (
            "BB_1pm",
            "BO_1pm",
            "1PM",
        ),
        (
            "BB_c1",
            "BO_c1",
            "C1",
        ),
        (
            "BB_4pm",
            "BO_4pm",
            "4PM",
        ),
        (
            "LBB",
            "LBO",
            "LAST",
        ),
    ]

    for bid_field, ask_field, label in spread_pairs:

        if not all(
            field in df.columns
            for field in [
                bid_field,
                ask_field,
            ]
        ):
            continue

        bid = numeric(
            df[bid_field]
        )

        ask = numeric(
            df[ask_field]
        )

        comparable = (
            bid.notna()
            & ask.notna()
        )

        negative_spread = (
            comparable
            & ((ask - bid) < 0)
        )

        zero_spread = (
            comparable
            & np.isclose(
                ask - bid,
                0,
                atol=1e-10,
            )
        )

        tests.extend(
            [
                {
                    "diagnostic": (
                        f"{label}_NEGATIVE_QUOTE_SPREAD"
                    ),
                    "test_type": (
                        "QUOTE_VALIDITY"
                    ),
                    "observations": int(
                        comparable.sum()
                    ),
                    "violations": int(
                        negative_spread.sum()
                    ),
                    "description": (
                        "Ask minus bid is negative."
                    ),
                },
                {
                    "diagnostic": (
                        f"{label}_LOCKED_QUOTE"
                    ),
                    "test_type": (
                        "QUOTE_STATE"
                    ),
                    "observations": int(
                        comparable.sum()
                    ),
                    "violations": int(
                        zero_spread.sum()
                    ),
                    "description": (
                        "Ask minus bid equals zero."
                    ),
                },
            ]
        )

    # -------------------------------------------------------------------------
    # Positive quote-price checks
    # -------------------------------------------------------------------------

    for field in QUOTE_PRICE_FIELDS:

        if field not in df.columns:
            continue

        s = numeric(
            df[field]
        )

        comparable = s.notna()

        nonpositive = (
            comparable
            & (s <= 0)
        )

        tests.append(
            {
                "diagnostic": (
                    f"{field}_POSITIVE"
                ),
                "test_type": (
                    "PRICE_VALIDITY"
                ),
                "observations": int(
                    comparable.sum()
                ),
                "violations": int(
                    nonpositive.sum()
                ),
                "description": (
                    f"{field} <= 0."
                ),
            }
        )

    quote_quality_df = pd.DataFrame(
        records
    )

    consistency_df = pd.DataFrame(
        tests
    )

    return (
        quote_quality_df,
        consistency_df,
    )


# =============================================================================
# TRADE PRICE QUALITY
# =============================================================================

def diagnose_trade_prices(df):

    tests = []

    for field in TRADE_PRICE_FIELDS:

        if field not in df.columns:
            continue

        s = numeric(
            df[field]
        )

        comparable = s.notna()

        nonpositive = (
            comparable
            & (s <= 0)
        )

        tests.append(
            {
                "diagnostic": (
                    f"{field}_POSITIVE"
                ),
                "test_type": (
                    "PRICE_VALIDITY"
                ),
                "observations": int(
                    comparable.sum()
                ),
                "violations": int(
                    nonpositive.sum()
                ),
                "description": (
                    f"{field} <= 0."
                ),
            }
        )

    return tests


# =============================================================================
# EXECUTION METRIC DIAGNOSTICS
# =============================================================================

def diagnose_execution_metrics(df):

    tests = []

    for field in EXECUTION_FIELDS:

        if field not in df.columns:
            continue

        s = numeric(
            df[field]
        )

        finite = (
            s.replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .dropna()
        )

        # Negative values are NOT automatically violations.
        #
        # Realized spread and price impact can be signed.
        #

        tests.append(
            {
                "diagnostic": (
                    f"{field}_NEGATIVE_OBSERVATIONS"
                ),
                "test_type": (
                    "DESCRIPTIVE"
                ),
                "observations": int(
                    finite.shape[0]
                ),
                "violations": int(
                    (finite < 0).sum()
                ),
                "description": (
                    "Negative values are "
                    "reported descriptively; "
                    "they are not treated as "
                    "invalid observations."
                ),
            }
        )

    return tests


# =============================================================================
# MAIN
# =============================================================================

def main():

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = load_data()

    # =========================================================================
    # TRADE DIAGNOSTICS
    # =========================================================================

    (
        trade_quality_df,
        trade_consistency_df,
    ) = diagnose_trade_quality(
        df
    )

    # =========================================================================
    # QUOTE DIAGNOSTICS
    # =========================================================================

    (
        quote_quality_df,
        quote_consistency_df,
    ) = diagnose_quote_quality(
        df
    )

    # =========================================================================
    # TRADE PRICE DIAGNOSTICS
    # =========================================================================

    trade_price_tests = (
        diagnose_trade_prices(
            df
        )
    )

    # =========================================================================
    # EXECUTION METRIC DIAGNOSTICS
    # =========================================================================

    execution_tests = (
        diagnose_execution_metrics(
            df
        )
    )

    # =========================================================================
    # COMBINE CONSISTENCY TESTS
    # =========================================================================

    consistency_df = pd.concat(
        [
            trade_consistency_df,
            quote_consistency_df,
            pd.DataFrame(
                trade_price_tests
            ),
            pd.DataFrame(
                execution_tests
            ),
        ],
        ignore_index=True,
    )

    # =========================================================================
    # SAVE OUTPUTS
    # =========================================================================

    trade_quality_df.to_csv(
        TRADE_OUTPUT,
        index=False,
    )

    quote_quality_df.to_csv(
        QUOTE_OUTPUT,
        index=False,
    )

    consistency_df.to_csv(
        CONSISTENCY_OUTPUT,
        index=False,
    )

    # =========================================================================
    # CONSOLE OUTPUT
    # =========================================================================

    print_header(
        "TRADE QUALITY SUMMARY"
    )

    if trade_quality_df.empty:

        print(
            "No trade-related fields detected."
        )

    else:

        print(
            trade_quality_df.to_string(
                index=False
            )
        )

    print_header(
        "QUOTE QUALITY SUMMARY"
    )

    if quote_quality_df.empty:

        print(
            "No quote-related fields detected."
        )

    else:

        print(
            quote_quality_df.to_string(
                index=False
            )
        )

    print_header(
        "MICROSTRUCTURE CONSISTENCY RESULTS"
    )

    if consistency_df.empty:

        print(
            "No consistency diagnostics generated."
        )

    else:

        display_df = (
            consistency_df[
                [
                    "diagnostic",
                    "test_type",
                    "observations",
                    "violations",
                    "description",
                ]
            ]
        )

        print(
            display_df.to_string(
                index=False
            )
        )

    # =========================================================================
    # IMPORTANT NEGATIVE EXECUTION METRIC REPORT
    # =========================================================================

    print_header(
        "NEGATIVE EXECUTION METRIC INTERPRETATION"
    )

    print(
        "Negative execution-related values were "
        "NOT treated as automatic data errors."
    )

    print(
        "Signed realized-spread and price-impact "
        "measures can legitimately take negative "
        "values depending on the underlying "
        "transaction-price and benchmark relationship."
    )

    print(
        "They require semantic validation rather "
        "than blanket removal."
    )

    # =========================================================================
    # OUTPUTS
    # =========================================================================

    print_header(
        "OUTPUTS"
    )

    print(
        f"Trade quality:\n{TRADE_OUTPUT}"
    )

    print(
        f"\nQuote quality:\n{QUOTE_OUTPUT}"
    )

    print(
        f"\nMicrostructure consistency:\n"
        f"{CONSISTENCY_OUTPUT}"
    )

    print_header(
        "STATUS"
    )

    print(
        "PASS — trade/quote/microstructure diagnostics generated."
    )

    print(
        "No observations were removed."
    )

    print(
        "No cleaning rules were applied."
    )


if __name__ == "__main__":
    main()