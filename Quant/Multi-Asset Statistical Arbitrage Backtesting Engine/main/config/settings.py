from dataclasses import dataclass

@dataclass
class BacktestConfig:
    start_date: str = "2017-01-01"
    end_date: str = "2026-01-01"
    initial_capital: float = 1_000_000
    base_currency: str = "USD"
    
@dataclass
class ExecutionConfig:
    comission_per_trade: float = 1.0
    bid_ask_spread_bps: float = 1.5
    slippage_vol_multiplier: float = 0.1
    rebalance_frequency: str = "daily"
    
@dataclass
class RiskConfig:
    max_leverage: float = 3.0
    max_drawdown: float = 0.25
    pair_stop_zscore: float = 4.0