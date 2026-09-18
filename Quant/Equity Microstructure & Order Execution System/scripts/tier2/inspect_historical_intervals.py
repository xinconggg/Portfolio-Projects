from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "tier2_historical_universe"
    / "crsp_tier2_historical_security_master.csv"
)

df = pd.read_csv(FILE)

df["effective_start"] = pd.to_datetime(df["effective_start"])
df["effective_end"] = pd.to_datetime(df["effective_end"])


# =============================================================================
# PERMNO INTERVAL COUNTS
# =============================================================================

print("=" * 80)
print("HISTORICAL INTERVAL COUNTS")
print("=" * 80)

counts = (
    df.groupby("permno")
      .size()
      .sort_values(ascending=False)
)

print(counts.to_string())


# =============================================================================
# MULTI-INTERVAL SECURITIES
# =============================================================================

print("\n" + "=" * 80)
print("PERMNOs WITH MULTIPLE HISTORICAL CLASSIFICATION INTERVALS")
print("=" * 80)

multi = counts[counts > 1].index

cols = [
    "permno",
    "ticker",
    "issuernm",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "issuertype",
    "primaryexch",
    "siccd",
    "effective_start",
    "effective_end",
    "research_classification",
]

print(
    df.loc[df["permno"].isin(multi), cols]
      .sort_values(["permno", "effective_start"])
      .to_string(index=False)
)


# =============================================================================
# DATE OVERLAP CHECK
# =============================================================================

print("\n" + "=" * 80)
print("DATE OVERLAP CHECK")
print("=" * 80)

overlaps = []

for permno, g in df.groupby("permno"):

    g = g.sort_values("effective_start").reset_index(drop=True)

    for i in range(1, len(g)):

        previous_end = g.loc[i - 1, "effective_end"]
        current_start = g.loc[i, "effective_start"]

        if current_start <= previous_end:
            overlaps.append({
                "permno": permno,
                "previous_end": previous_end,
                "current_start": current_start,
            })

overlap_df = pd.DataFrame(overlaps)

if overlap_df.empty:
    print("PASS: No overlapping historical intervals detected.")
else:
    print("FAIL: Overlapping intervals detected.")
    print(overlap_df.to_string(index=False))