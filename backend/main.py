from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np
from pypfopt import expected_returns, risk_models
from typing import List
import warnings
warnings.filterwarnings('ignore')

app = FastAPI(title="Investment Analysis API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Example universe of assets
ASSET_UNIVERSE = {
    "Stocks": {
        "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA"],
        "Healthcare": ["JNJ", "PFE", "UNH"],
        "Finance": ["JPM", "BAC", "V"],
    },
    "ETFs": ["SPY", "QQQ", "EFA", "EEM"],
    "Commodities": ["GLD", "SLV", "USO"]
}

@app.get("/api/universe")
def get_universe():
    return ASSET_UNIVERSE

def get_historical_data(tickers: List[str], period: str = "10y"):
    """Fetch historical closing prices."""
    if not tickers:
        return pd.DataFrame()
    data = yf.download(tickers, period=period, progress=False)['Close']
    if len(tickers) == 1:
        data = pd.DataFrame(data)
        data.columns = tickers
    return data

@app.post("/api/analyze")
def analyze_assets(tickers: List[str] = Query(default=["AAPL", "MSFT"])):
    """Analyze a list of tickers, calculating expected returns, risk, and analyst targets."""
    # 1. Fetch 10-year historical data
    hist_data = get_historical_data(tickers, period="10y")
    if hist_data.empty:
        return {"error": "No data found for provided tickers."}
    
    # 2. Modern Portfolio Theory (Mean-Variance & CAPM approximation)
    # Calculate expected annualized returns (using mean historical returns as a simple expectation)
    mu = expected_returns.mean_historical_return(hist_data)
    # Calculate annualized sample covariance matrix
    S = risk_models.sample_cov(hist_data)
    # Extract standard deviation (volatility) as risk
    volatility = pd.Series(np.sqrt(np.diag(S)), index=S.index)
    
    # 3. Gather Analyst Estimates & Basic WACC Components (Proxy)
    results = []
    
    for ticker in tickers:
        ticker_info = yf.Ticker(ticker).info
        
        # Risk & Return from historical
        exp_return = mu.get(ticker, 0)
        risk = volatility.get(ticker, 0)
        
        # Analyst Targets
        target_mean_price = ticker_info.get("targetMeanPrice", None)
        current_price = ticker_info.get("currentPrice", ticker_info.get("regularMarketPrice", None))
        
        analyst_upside = None
        if target_mean_price and current_price:
            analyst_upside = (target_mean_price - current_price) / current_price
            
        # Proxy WACC approximation (very simplified for automated large-scale processing)
        # In reality WACC requires detailed debt/equity breakdown and corporate tax rates.
        beta = ticker_info.get("beta", 1.0)
        risk_free_rate = 0.04 # Assume 4% RFR
        market_return = 0.10 # Assume 10% expected market return
        # CAPM Cost of Equity
        cost_of_equity = risk_free_rate + beta * (market_return - risk_free_rate)
        
        results.append({
            "ticker": ticker,
            "name": ticker_info.get("shortName", ticker),
            "sector": ticker_info.get("sector", "Unknown"),
            "country": ticker_info.get("country", "Unknown"),
            "current_price": current_price,
            "historical_expected_return": exp_return,
            "volatility_risk": risk,
            "sharpe_ratio": (exp_return - risk_free_rate) / risk if risk > 0 else 0,
            "analyst_target_price": target_mean_price,
            "analyst_expected_return": analyst_upside,
            "beta": beta,
            "capm_cost_of_equity": cost_of_equity,
        })
    
    # 4. Rank by Sharpe Ratio (Risk vs Expectation)
    results.sort(key=lambda x: x["sharpe_ratio"], reverse=True)
    top_10 = results[:10]
    
    # Prepare historical data for plotting
    # Downsample or limit points to prevent massive JSON payload
    hist_data.index = hist_data.index.astype(str)
    # Resample to monthly to reduce data points
    monthly_data = hist_data.iloc[::20, :]
    plot_data = monthly_data.reset_index().to_dict(orient="records")
    
    return {
        "analysis": results,
        "top_10": top_10,
        "plot_data": plot_data
    }
