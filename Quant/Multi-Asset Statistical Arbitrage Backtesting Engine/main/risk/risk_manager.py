import pandas as pd
import numpy as np

class RiskManager:
    """
    Applies portfolio-level risk controls to limit losses and exposure.

    Controls being Implemented:
    - Maximum Drawdown Stop
    - Maximum Leverage Cap
    """
    def __init__(self, max_drawdown=0.2, max_leverage=3.0):
        self.max_drawdown = max_drawdown
        self.max_leverage = max_leverage

    def enforce_drawdown(self, pnl: pd.Series):
        """
        Enforce a maximum drawdown rule.
        If the current drawdown exceeds the allowed limit, halt the strategy (flatten all positions)
        
        Inputs:
        - pnl: Cumulative PnL

        Outputs:
        - pnl (pd.Series): If within limits, return original pnl. Else, returns a zero series indicating trading has stopped.
        """
        # Track peak of PnL 
        peak = pnl.cummax() 

        # Compute drawdown as percentage of peak
        drawdown = (peak-pnl) / peak

        # If latest drawdown exceeds limit, stop trading (flatten all position)
        if drawdown.iloc[-1] > self.max_drawdown:
            return pd.Series(0, index=pnl.index)
        # Else return original PnL
        return pnl
    
    def enforce_leverage(self, positions: pd.Series, max_leverage=None):
        """
        Enforce a maximum levereage constraint on portfolio positions.

        Inputs:
        - positions: Portfolio positions
        - max_leverage: Override default leverage limit (if entered)

        Outputs:
        - positions: If limit not exceeded, return original positions. Else, return scaled positions.
        """
        if max_leverage is None:
            max_leverage = self.max_leverage

        # Total Leverage = sum of absolute positions
        total_leverage = np.abs(positions).sum()

        # Scale positions proportionally if leverage is too high
        if total_leverage > max_leverage:
            scaling = max_leverage / total_leverage
            return positions * scaling
        # If leverage limit not exceeded
        return positions