import pandas as pd

class PortfolioManager:
    """
    Manages a portfolio consisting of multiple pairs, allowing aggregation and enforcing leverage/exposure limits.

    Key Features:
    - Add individual pair positions
    - Aggregate positions across all pairs
    - Apply a maximum leverage cap to control risk
    """
    def __init__(self, max_leverage: float=3.0):
        self.max_leverage = max_leverage
        self.positions = pd.DataFrame()

    def add_pair(self, pair_name:str, positions:pd.Series):
        """
        Add a new pair's position to the portfolio.

        Input:
        - pair_name: Identifier for the pair
        - positions: Positions of the pair over time
        """
        self.positions[pair_name] = positions

    def aggregate(self):
        """
        Aggregate positions across all pairs and enforce leverage limits.

        Steps:
        1) Compute total exposure (sum of absolute positions)
        2) Compute scaling factor to limit leverage
        3) Scale all pair positions proportionally
        4) Sum scaled positions to get total portfolio exposure per time step

        Output:
        - net_agg_position (pd.Series): Aggregated portfolio position over time
        """
        # Total exposure
        total_exposure = self.positions.abs().sum(axis=1)

        # Scaling factor:
        # - If total exposure < max leverage, then scaling factor = 1 (no scaling)
        # - If total exposure > max leverage, then scale down proportionally
        scaling_factor = (self.max_leverage / total_exposure).clip(upper=1.0)

        # Apply scaling factor to each pair's position
        agg_positions = self.positions.multiply(scaling_factor, axis=0)

        # Sum agg_positions across all pairs to get net portfolio positions
        net_agg_position = agg_positions.sum(axis=1)
        return net_agg_position