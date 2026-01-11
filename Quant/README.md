# [Multi-Asset Statistical Arbitrage Backtesting Engine](https://github.com/xinconggg/Portfolio-Projects/tree/main/Quant/Multi-Asset%20Statistical%20Arbitrage%20Backtesting%20Engine)

---
## Project Overview
This project implements an **end-to-end statistical arbitrage backtesting engine** across multiple asset classes (equities, ETFs, and FX).  
It is designed to demonstrate:

- **Trading intuition**: selection of cointegrated pairs, mean-reversion strategies, and spread dynamics  
- **Statistical rigor**: cointegration testing, half-life estimation, false discovery control  
- **Risk awareness**: drawdown management, leverage limits, execution frictions  
- **Modular engineering**: reusable, production-style Python architecture  
---

## Key Features
1. **Data Engineering**  
   - Free-data sourcing from Yahoo Finance, FRED, Stooq  
   - Data cleaning: missing values, corporate actions, outlier handling  
   - Time alignment across asset classes and efficient handling of large datasets  

2. **Statistical Research**  
   - Pair selection via rolling correlation and cointegration (Engle-Granger, Johansen)  
   - Spread construction and normalization (z-score, half-life estimation)  
   - Mean-reversion diagnostics including ADF test and Hurst exponent  
   - Regime filtering for trend and volatility  

3. **Signal Generation**  
   - Entry/exit logic based on z-score thresholds and dynamic bands  
   - Time-based exits and signal debouncing  
   - Handling conflicting signals across multiple pairs  

4. **Portfolio Construction**  
   - Dollar-neutral and volatility-targeted positions  
   - Risk parity across pairs with sector/asset exposure constraints  
   - Capital allocation and leverage management  

5. **Execution & Market Frictions**  
   - Realistic transaction costs, bid-ask spreads, and slippage  
   - Trade latency and rebalancing frequency  

6. **Risk Management**  
   - Pair-level and portfolio-level stop-loss logic  
   - Drawdown-based risk reduction  
   - Max leverage and exposure caps  
   - Stress testing under historical volatility spikes  

7. **Performance Evaluation**  
   - Sharpe, Sortino, Calmar ratios  
   - Max drawdown, recovery time, hit rate, payoff ratio  
   - Turnover, capacity constraints, rolling performance metrics  

8. **Visualization & Dashboarding**  
   - Equity curve and drawdowns  
   - Spread & z-score dynamics  
   - Pair-level PnL attribution  
   - Rolling Sharpe and volatility  

9. **Validation & Robustness Checks**  
   - Parameter sensitivity analysis (entry/exit thresholds, max hold)  
   - Subperiod analysis and cross-asset generalization  
   - False discovery control to prevent spurious pair selection  
---

## Insights
### Asset Universe
| Asset Class | Tickers / Examples                   | Notes |
|------------|-------------------------------------|-------|
| Equities   | AAPL, MSFT, GOOG, AMZN, TSLA, NVDA, AMD, META, JPM, KO, PEP, XOM, CVX        | Top liquidity S&P500 names |
| ETFs       | XLK, XLF, XLE, XLY, XLV             | Sector ETFs with >5yr history |
| FX         | EUR/USD, USD/JPY, GBP/USD           | G10 daily FX pairs |

### Cointegrated Pairs (Equities)

<img width="405" height="153" alt="Cointegrated Pairs" src="https://github.com/user-attachments/assets/d0a5688c-39fa-4ece-9a6d-1651bf5281c2" />

### Spread, Z-score and Generated Signals for Top Cointegrated Pair (AAPL & KO)

<img width="980" height="528" alt="Spread Zscore" src="https://github.com/user-attachments/assets/3aa2547a-e455-4d4d-bb8f-1df55dbe261e" />

### Performance Evaluation Metrics
<img width="269" height="116" alt="Performance Metrics" src="https://github.com/user-attachments/assets/f975427c-dbac-4b21-8625-a627abcac70b" />

### Portfolio Equity Curve
<img width="1584" height="450" alt="newplot" src="https://github.com/user-attachments/assets/68b97be5-d270-41e7-a723-859e90ed551c" />

### Portfolio Drawdowns
<img width="1584" height="450" alt="Portfolio Drawdowns" src="https://github.com/user-attachments/assets/0b11e9a1-5cee-4ba8-b80c-7029678ec34c" />

### Rolling Sharpe Ratio
<img width="1584" height="450" alt="Rolling Sharpe Ratio" src="https://github.com/user-attachments/assets/641804d9-c083-4b69-85dd-1ea0844fbb6b" />
