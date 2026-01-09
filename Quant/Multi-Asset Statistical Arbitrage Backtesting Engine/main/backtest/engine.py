class BacktestEngine:
    """
    Event-driven backtesting engine.
    Coordinates data, signals, portfolio, execution and risk.
    """
    
    def __init__(self,
                 data_handler,
                 signal_generator,
                 portfolio,
                 execution_model,
                 risk_manager):
        self.data_handler = data_handler
        self.signal_generator = signal_generator
        self.portfolio = portfolio
        self.execution_model = execution_model
        self.risk_manager = risk_manager
        
    def run(self):
        """
        Main backtest loop.
        """
        raise NotImplementedError("Backtest loop implemented in later phase.")
        