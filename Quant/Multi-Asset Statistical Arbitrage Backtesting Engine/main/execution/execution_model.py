import pandas as pd
import numpy as np

class ExecutionModel:
    """
    Models realistic market frictions (impact) in a trading strategy:
    1) Transaction Costs (Commissions per unit traded)
    2) Bid-Ask Spread Impact
    3) Slippage

    This allows the backtest to more closely approximate real-world performance.
    """
    def __init__(self, transaction_cost=0.0005, bid_ask_spread=0.0002, slippage_vol_factor=0.1):
        """
        Initialize execution model parameters.

        Inputs:
        - transaction_cost: cost per unit traded (0.05% of trade in this case)
        - bid_ask_spread: half_spread appread per trade
        - slippage_vol_factor: fraction of recent volatility applied as additional slippage
        """
        self.transaction_cost = transaction_cost
        self.bid_ask_spread = bid_ask_spread
        self.slippage_vol_factor = slippage_vol_factor

    def apply(self, positions: pd.Series, prices: pd.Series):
        """
        Apply execution frictions to positions and return effective prices.

        Inputs:
        - positions: Desired positions over time
        - prices: Market prices

        Outputs:
        - adjusted_prices (pd.Series): Prices adjusted for realistic trading costs
        """
        # Compute trades (i.e. no. of position changes)
        trades = positions.diff().fillna(positions.iloc[0])

        # Transaction cost
        transc_cost = np.abs(trades) * self.transaction_cost

        # Bid-ask spread impact
        ba_spread_impact = np.sign(trades) * self.bid_ask_spread * prices

        # Slippage (Rolling 5-day standard deviation as proxy for short-term volatility)
        vol = prices.pct_change().rolling(5).std().fillna(0)
        slippage = np.sign(trades) * vol * self.slippage_vol_factor * prices

        # Total friction (impact)
        total_impact = transc_cost + ba_spread_impact + slippage

        # Adjusted price, reflecting realistic execution
        adjusted_prices = prices + total_impact
        return adjusted_prices