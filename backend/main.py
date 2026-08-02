from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np
import math
from pypfopt import expected_returns, risk_models
from statsmodels.tsa.statespace.sarimax import SARIMAX
from typing import List
import warnings
warnings.filterwarnings('ignore')

import os

app = FastAPI(title="Investment Analysis API")

# Secure CORS: Allow specific origins (localhost for dev, and production URL)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "http://localhost:3000,https://stock.webtvmedia.net"
).split(",")

# Enable CORS for frontend securely
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"], # Restricted from "*" to specific methods
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
def analyze_assets(
    tickers: List[str] = Query(default=["AAPL", "MSFT"]),
    quant_method: str = Query(default="sharpe", description="Quantitative method to rank by: sharpe, sortino, treynor")
):
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
        
        # Clean NaN values which break JSON serialization
        if pd.isna(exp_return): exp_return = 0.0
        if pd.isna(risk): risk = 0.0
        
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
        
        # Calculate Advanced Quantitative Ratios
        treynor_ratio = (exp_return - risk_free_rate) / beta if beta and beta != 0 else 0
        
        returns_series = ticker_hist.pct_change().dropna()
        downside_returns = returns_series[returns_series < 0]
        downside_std = downside_returns.std() * np.sqrt(252) if not downside_returns.empty else 0
        sortino_ratio = (exp_return - risk_free_rate) / downside_std if downside_std > 0 else 0
        
        # Black-Scholes / Geometric Brownian Motion 1-Year Min/Max Estimation (95% Confidence)
        bs_min_1y = None
        bs_max_1y = None
        if current_price and current_price > 0 and risk > 0:
            drift = exp_return - 0.5 * (risk ** 2)
            diffusion = 1.96 * risk # 1.96 standard deviations for 95% CI
            bs_min_1y = current_price * math.exp(drift - diffusion)
            bs_max_1y = current_price * math.exp(drift + diffusion)
            
        # SARIMA 1-Year Forecast (using Monthly Data to keep it fast)
        sarima_forecast = None
        try:
            # Resample to monthly and drop NA
            monthly_series = ticker_hist.resample('ME').last().dropna()
            if len(monthly_series) > 24:
                # Simple ARIMA(1,1,0) to be extremely fast and avoid convergence errors
                model = SARIMAX(monthly_series, order=(1, 1, 0))
                model_fit = model.fit(disp=False)
                # Forecast 12 months ahead
                forecast = model_fit.forecast(steps=12)
                sarima_forecast = float(forecast.iloc[-1])
        except Exception as e:
            sarima_forecast = None

        # Reinforcement Learning (RL) Proxy Agent Action
        rl_action = "HOLD"
        rl_confidence = 50.0
        try:
            if len(ticker_hist) > 200:
                ma50 = ticker_hist.rolling(window=50).mean().iloc[-1]
                ma200 = ticker_hist.rolling(window=200).mean().iloc[-1]
                
                # RSI 14
                delta = ticker_hist.diff()
                up = delta.clip(lower=0)
                down = -1 * delta.clip(upper=0)
                ema_up = up.ewm(com=13, adjust=False).mean()
                ema_down = down.ewm(com=13, adjust=False).mean()
                rs = ema_up / ema_down
                rsi = 100 - (100 / (1 + rs))
                current_rsi = float(rsi.iloc[-1])
                
                # Q-Learning Policy Heuristic
                # State: (Trend, RSI) -> Action
                if ma50 > ma200:
                    if current_rsi < 40:
                        rl_action = "STRONG BUY"
                        rl_confidence = 90.0
                    elif current_rsi < 70:
                        rl_action = "BUY"
                        rl_confidence = 75.0
                    else:
                        rl_action = "HOLD"
                        rl_confidence = 55.0
                else:
                    if current_rsi > 60:
                        rl_action = "STRONG SELL"
                        rl_confidence = 85.0
                    elif current_rsi > 40:
                        rl_action = "SELL"
                        rl_confidence = 70.0
                    else:
                        rl_action = "HOLD (Oversold)"
                        rl_confidence = 60.0
        except Exception:
            pass
        
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
            "bs_min_1y_estimation": bs_min_1y,
            "bs_max_1y_estimation": bs_max_1y,
            "sarima_1y_forecast": sarima_forecast,
            "rl_action": rl_action,
            "rl_action": rl_action,
            "rl_confidence": rl_confidence,
            "treynor_ratio": treynor_ratio,
            "sortino_ratio": sortino_ratio
        })
    
    # 4. Rank by selected Quantitative Method
    if quant_method == "sortino":
        results.sort(key=lambda x: x.get("sortino_ratio", 0), reverse=True)
    elif quant_method == "treynor":
        results.sort(key=lambda x: x.get("treynor_ratio", 0), reverse=True)
    else:
        results.sort(key=lambda x: x.get("sharpe_ratio", 0), reverse=True)
        
    top_10 = results[:10]
    
    # Prepare historical data for plotting
    # Downsample or limit points to prevent massive JSON payload
    hist_data.index = hist_data.index.astype(str)
    # Resample to monthly to reduce data points, and fill NaNs
    monthly_data = hist_data.iloc[::20, :].ffill().bfill().fillna(0)
    plot_data = monthly_data.reset_index().to_dict(orient="records")
    
    return {
        "analysis": results,
        "top_10": top_10,
        "plot_data": plot_data
    }
