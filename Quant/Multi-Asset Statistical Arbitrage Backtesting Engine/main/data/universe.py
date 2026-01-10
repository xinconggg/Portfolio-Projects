def get_universe():
    """
    Returns a dictionary of asset classes and tickers
    """
    equities = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "NVDA", "AMD", "META", "JPM", "KO", "PEP", "XOM", "CVX"]
    etfs = ["XLK", "XLF", "XLE", "XLY", "XLV"]
    fx = ["EURUSD=X", "JPY=X", "GBPUSD=X"]
    
    return {"equities": equities, "etfs": etfs, "fx": fx}