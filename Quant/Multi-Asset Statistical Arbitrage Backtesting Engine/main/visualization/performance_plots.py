import pandas as pd
import numpy as np
import plotly.graph_objects as go

def plot_equity_curve(returns: pd.Series):
    """
    Plot cumulative portfolio equity curve from return series.
    """
    # Convert returns into cumulative equity
    equity = (1+returns).cumprod()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity.index,
        y=equity.values,
        name="Equity Curve"
    ))
    fig.update_layout(
        title="Portfolio Equity Curve",
        xaxis_title="Date",
        yaxis_title="Cumulative Return"
    )
    return fig

def plot_drawdown(returns: pd.Series):
    """
    Plot portfolio drawdown over time.

    Drawdown = (Peak Equity - Current Equity) / Peak Equity
    """
    # Compute drawdown
    equity = (1+returns).cumprod()
    peak = equity.cummax()
    drawdown = (peak - equity) / peak

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=drawdown.index,
        y=drawdown.values,
        name="Drawdown",
        fill="tozeroy"
    ))
    fig.update_layout(
        title="Portfolio Drawdown",
        xaxis_title="Date",
        yaxis_title="Drawdown"
    )
    return fig

def plot_rolling_sharpe(returns: pd.Series, window=63):
    """
    Plot rolling annualized Sharpe Ratio.

    windows=63: 3 Months of trading days
    """
    # Compute rolling sharpe ratio
    rolling_sharpe = (returns.rolling(window).mean() / returns.rolling(window).std()) * np.sqrt(252)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rolling_sharpe.index,
        y=rolling_sharpe.values,
        name="Rolling Sharpe"
    ))
    fig.update_layout(
        title="Rolling Sharpe Ratio",
        xaxis_title="Date",
        yaxis_title="Sharpe"
    )
    return fig