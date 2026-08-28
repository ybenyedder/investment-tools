# Portfolio Strategy Scenarios (Multi-Time Horizon)

I have run a Monte Carlo simulation over the past 10 years of market data using Modern Portfolio Theory to detect the **best opportunities** and simulate how to optimally spread capital across portfolios of varying sizes and time horizons.

## Top 10 Best Opportunities (Risk-Adjusted)

| Rank | Asset | Exp. Annual Return | Annual Risk (Vol) | Sharpe Ratio |
|---|---|---|---|---|
| 1 | **NVDA** | 64.6% | 50.1% | 1.21 |
| 2 | **LLY** | 33.1% | 30.5% | 0.95 |
| 3 | **AAPL** | 29.4% | 29.1% | 0.87 |
| 4 | **TSM** | 34.0% | 34.8% | 0.86 |
| 5 | **AMD** | 51.3% | 57.0% | 0.83 |
| 6 | **MSFT** | 26.0% | 27.7% | 0.79 |
| 7 | **COST** | 21.2% | 22.1% | 0.78 |
| 8 | **ASML** | 33.2% | 39.2% | 0.75 |
| 9 | **QQQ** | 20.8% | 22.6% | 0.74 |
| 10 | **GOOGL** | 24.3% | 29.5% | 0.69 |

---

## Monte Carlo Projections by Portfolio Size & Time Horizon

### Small ($10K)
**Strategy:** Spread across top 4 assets.
* **Assets:** NVDA, LLY, AAPL, TSM
* **Expected Annual Return:** 40.3% | **Volatility:** 26.9%

| Time Horizon | Pessimistic (5th %) | Expected (Median) | Optimistic (95th %) |
|---|---|---|---|
| 1 Year | $9,245 | **$14,418** | $22,442 |
| 5 Years | $23,109 | **$62,419** | $167,892 |
| 10 Years | $95,666 | **$389,970** | $1,580,290 |
| 20 Years | $2,087,202 | **$15,227,369** | $110,166,518 |

### Medium ($100K)
**Strategy:** Spread across top 10 assets.
* **Assets:** NVDA, LLY, AAPL, TSM, AMD, MSFT, COST, ASML, QQQ, GOOGL
* **Expected Annual Return:** 33.8% | **Volatility:** 25.3%

| Time Horizon | Pessimistic (5th %) | Expected (Median) | Optimistic (95th %) |
|---|---|---|---|
| 1 Year | $89,315 | **$135,697** | $205,803 |
| 5 Years | $180,914 | **$460,940** | $1,169,781 |
| 10 Years | $566,564 | **$2,126,484** | $7,936,978 |
| 20 Years | $6,974,452 | **$45,274,380** | $291,590,238 |

### Large ($1M)
**Strategy:** Spread across top 15 assets.
* **Assets:** NVDA, LLY, AAPL, TSM, AMD, MSFT, COST, ASML, QQQ, GOOGL, JPM, SPY, WMT, MA, TSLA
* **Expected Annual Return:** 30.0% | **Volatility:** 22.9%

| Time Horizon | Pessimistic (5th %) | Expected (Median) | Optimistic (95th %) |
|---|---|---|---|
| 1 Year | $900,484 | **$1,314,776** | $1,916,615 |
| 5 Years | $1,688,173 | **$3,935,247** | $9,140,684 |
| 10 Years | $4,682,534 | **$15,498,234** | $51,038,018 |
| 20 Years | $44,251,976 | **$240,459,879** | $1,297,346,463 |

### Huge ($10M)
**Strategy:** Spread across top 25 assets.
* **Assets:** NVDA, LLY, AAPL, TSM, AMD, MSFT, COST, ASML, QQQ, GOOGL, JPM, SPY, WMT, MA, TSLA, V, GLD, TXN, ENPH, JNJ, NEE, UNH, XOM, PG, TLT
* **Expected Annual Return:** 23.5% | **Volatility:** 18.7%

| Time Horizon | Pessimistic (5th %) | Expected (Median) | Optimistic (95th %) |
|---|---|---|---|
| 1 Year | $9,122,266 | **$12,419,811** | $16,887,396 |
| 5 Years | $14,842,127 | **$29,590,794** | $58,824,032 |
| 10 Years | $33,022,125 | **$87,617,111** | $231,519,549 |
| 20 Years | $193,306,650 | **$768,365,295** | $3,036,435,646 |

