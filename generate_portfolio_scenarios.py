import yfinance as yf
import pandas as pd
import numpy as np
import math
from pypfopt import expected_returns, risk_models

UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "NVDA", "TSLA",
    "TSM", "ASML", "AMD", "TXN",
    "JPM", "V", "MA",
    "JNJ", "UNH", "LLY",
    "WMT", "PG", "COST",
    "XOM", "NEE", "ENPH",
    "SPY", "QQQ", "TLT", "GLD"
]

def run_scenarios():
    print("Fetching historical data for 10 years...")
    data = yf.download(UNIVERSE, period="10y", auto_adjust=True, progress=False)["Close"]
    data = data.ffill().dropna(how="all")
    
    mu = expected_returns.mean_historical_return(data)
    S = risk_models.sample_cov(data)
    
    risk_free_rate = 0.04
    sharpe_ratios = {}
    for ticker in UNIVERSE:
        ret = mu[ticker]
        vol = math.sqrt(S.loc[ticker, ticker])
        sharpe = (ret - risk_free_rate) / vol if vol > 0 else 0
        sharpe_ratios[ticker] = {"ret": ret, "vol": vol, "sharpe": sharpe}
        
    ranked = sorted(sharpe_ratios.items(), key=lambda x: x[1]["sharpe"], reverse=True)
    
    scenarios = [
        {"name": "Small ($10K)", "capital": 10000, "top_n": 4},
        {"name": "Medium ($100K)", "capital": 100000, "top_n": 10},
        {"name": "Large ($1M)", "capital": 1000000, "top_n": 15},
        {"name": "Huge ($10M)", "capital": 10000000, "top_n": 25},
    ]
    
    with open("portfolio_scenarios.md", "w") as f:
        f.write("# Portfolio Strategy Scenarios (Multi-Time Horizon)\n\n")
        f.write("I have run a Monte Carlo simulation over the past 10 years of market data using Modern Portfolio Theory to detect the **best opportunities** and simulate how to optimally spread capital across portfolios of varying sizes and time horizons.\n\n")
        
        f.write("## Top 10 Best Opportunities (Risk-Adjusted)\n\n")
        f.write("| Rank | Asset | Exp. Annual Return | Annual Risk (Vol) | Sharpe Ratio |\n")
        f.write("|---|---|---|---|---|\n")
        for i, (ticker, metrics) in enumerate(ranked[:10]):
            f.write(f"| {i+1} | **{ticker}** | {metrics['ret']*100:.1f}% | {metrics['vol']*100:.1f}% | {metrics['sharpe']:.2f} |\n")
        
        f.write("\n---\n\n## Monte Carlo Projections by Portfolio Size & Time Horizon\n\n")
        
        for sc in scenarios:
            capital = sc["capital"]
            top_n = min(sc["top_n"], len(ranked))
            selected_tickers = [x[0] for x in ranked[:top_n]]
            weights = np.array([1.0 / top_n] * top_n)
            
            mu_sub = np.array([mu[t] for t in selected_tickers])
            cov_sub = S.loc[selected_tickers, selected_tickers].values
            
            port_ret = np.dot(weights, mu_sub)
            port_vol = math.sqrt(np.dot(weights.T, np.dot(cov_sub, weights)))
            
            f.write(f"### {sc['name']}\n")
            f.write(f"**Strategy:** Spread across top {top_n} assets.\n")
            f.write(f"* **Assets:** {', '.join(selected_tickers)}\n")
            f.write(f"* **Expected Annual Return:** {port_ret*100:.1f}% | **Volatility:** {port_vol*100:.1f}%\n\n")
            
            np.random.seed(42)
            n_sims = 10000
            Z = np.random.standard_normal(n_sims)
            drift = port_ret - 0.5 * port_vol**2
            
            f.write("| Time Horizon | Pessimistic (5th %) | Expected (Median) | Optimistic (95th %) |\n")
            f.write("|---|---|---|---|\n")
            
            for years in [1, 5, 10, 20]:
                diffusion = port_vol * math.sqrt(years)
                final_values = capital * np.exp(drift * years + diffusion * Z)
                p5 = np.percentile(final_values, 5)
                p50 = np.percentile(final_values, 50)
                p95 = np.percentile(final_values, 95)
                f.write(f"| {years} Year{'s' if years>1 else ''} | ${p5:,.0f} | **${p50:,.0f}** | ${p95:,.0f} |\n")
            
            f.write("\n")

if __name__ == "__main__":
    run_scenarios()
