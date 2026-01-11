import pandas as pd
import numpy as np
import plotly.graph_objects as go

def plot_spread_zscore(spread: pd.Series, zscore: pd.Series):
    """
    Plot spread and its corresponding z-score on dual y-axis.

    Useful for Visually Validating:
    - Mean Reversion Behavior
    - Entry/Exit Signal Quality
    - Regime Shifts in Spread Dynamics
    """
    fig = go.Figure()

    # Raw spread (left axis)
    fig.add_trace(go.Scatter(
        x=spread.index,
        y=spread.values,
        name="Spread"
    ))

    # Z-score (right axis)
    fig.add_trace(go.Scatter(
        x=zscore.index,
        y=zscore.values,
        name="Z-score",
        yaxis="y2"
    ))

    fig.update_layout(
        title="Spread and Z-score Dynamics",
        yaxis=dict(title="Spread"),
        yaxis2=dict(
            title="Z-score",
            overlaying="y",
            side="right"
        )
    )
    return fig

def plot_pair_pnl(pair_returns: dict):
    """
    Plot cumulative PnL for each individual trading pair.

    Helps to Identify:
    - Strong vs Weak Pair
    - Diversification Benefits
    - Pairs Contributing most to Drawdowns
    """
    fig = go.Figure()
    
    for pair, ret in pair_returns.items():
        # Fill NaNs
        ret = ret.fillna(0)
        # Clip extreme returns
        ret = np.clip(ret, -1 + 1e-10, 10)
        pnl = (1 + ret).cumprod()
        fig.add_trace(go.Scatter(
            x=pnl.index,
            y=pnl.values,
            name=pair
        ))
    
    fig.update_layout(
        title="Pair-Level PnL Attribution",
        xaxis_title="Date",
        yaxis_title="Cumulative Return"
    )
    return fig