from pymongo import MongoClient
import datetime
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np
import math
from pypfopt import expected_returns, risk_models
from statsmodels.tsa.statespace.sarimax import SARIMAX
from typing import List, Optional
from pydantic import BaseModel
import warnings
warnings.filterwarnings('ignore')

import os
import requests
from io import StringIO

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
    "US Markets (NASDAQ & NYSE)": {
        "Big Tech / AI": ["AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "TSLA", "AMD", "INTC", "TSM", "ASML", "AVGO", "CSCO"],
        "Power & Energy Storage": ["FLNC", "ENPH", "SEDG", "ALB", "FSLR", "PLUG"],
        "Finance": ["JPM", "BAC", "V", "MA", "GS", "MS"],
        "Healthcare": ["JNJ", "PFE", "UNH", "LLY", "ABBV"],
        "Consumer": ["WMT", "PG", "KO", "PEP", "MCD", "NKE"],
    },
    "Europe (CAC40, DAX, FTSE, MIB)": {
        "France (CAC 40)": ["MC.PA", "OR.PA", "RMS.PA", "TTE.PA", "SAN.PA", "AIR.PA", "BNP.PA"],
        "Germany (DAX)": ["SAP.DE", "SIE.DE", "ALV.DE", "DTE.DE", "VOW3.DE", "MBG.DE"],
        "UK (FTSE 100)": ["AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "BATS.L"],
        "Italy (MIB)": ["ENEL.MI", "ENI.MI", "ISP.MI", "STLA.MI", "UCG.MI", "RACE.MI"],
    },
    "Asia (Nikkei, Chinese, Hang Seng)": {
        "Japan (Nikkei 225)": ["7203.T", "6758.T", "9984.T", "8306.T", "6861.T"],
        "China & Hong Kong": ["TCEHY", "BABA", "0700.HK", "9988.HK", "BIDU", "JD", "NIO", "PDD"],
        "India & Emerging": ["RELIANCE.NS", "TCS.NS", "INFY", "HDB"],
    },
    "Funds & Commodities": {
        "Global & Regional ETFs": ["SPY", "QQQ", "VGK", "VWO", "INDA", "MCHI", "EWJ", "EWU"],
        "World ETFs": ["VT", "ACWI", "URTH", "VXUS", "VEU", "IOO"],
        "Commodities": ["GLD", "SLV", "USO", "UNG", "CPER"],
    }
}

try:
    # Dynamically fetch S&P 500 from Wikipedia with proper User-Agent
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', headers=headers)
    sp500_table = pd.read_html(StringIO(r.text))[0]
    sp500_tickers = sp500_table['Symbol'].tolist()
    sp500_tickers = [t.replace('.', '-') for t in sp500_tickers] # format for yfinance
    ASSET_UNIVERSE["US Markets (NASDAQ & NYSE)"]["S&P 500"] = sp500_tickers
except Exception as e:
    print(f"Failed to fetch S&P 500: {e}")

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
    
    # Calculate Correlation Matrix to extract parameters that correlate
    corr_matrix = hist_data.pct_change().corr()
    
    # 3. Gather Analyst Estimates & Basic WACC Components (Proxy)
    results = []
    
    for ticker in tickers:
        yf_ticker = yf.Ticker(ticker)
        ticker_info = yf_ticker.info
        ticker_hist = hist_data[ticker].dropna() if ticker in hist_data.columns else pd.Series()
        
        # Extract Historical Financials
        try:
            income = yf_ticker.income_stmt
            bs = yf_ticker.balance_sheet
            cf = yf_ticker.cashflow
            
            def extract_metric(df, possible_names):
                for name in possible_names:
                    if name in df.index:
                        return df.loc[name].dropna()
                return pd.Series(dtype=float)

            rev_series = extract_metric(income, ["Total Revenue", "Operating Revenue"])
            ni_series = extract_metric(income, ["Net Income", "Net Income Common Stockholders", "Net Income Continuous Operations"])
            opex_series = extract_metric(income, ["Operating Expense", "Total Operating Expenses"])
            capex_series = extract_metric(cf, ["Capital Expenditure", "Capital Expenditures"])
            debt_series = extract_metric(bs, ["Total Debt"])
            cash_series = extract_metric(bs, ["Cash And Cash Equivalents", "Cash", "Cash Cash Equivalents And Short Term Investments"])
            
            def process_series(s):
                if s.empty: return {}, 0.0
                d = {k.strftime('%Y'): float(v) for k, v in s.items()}
                s_sorted = s.sort_index(ascending=True)
                pct_changes = s_sorted.pct_change().dropna()
                vol = float(pct_changes.std()) if not pct_changes.empty else 0.0
                if pd.isna(vol): vol = 0.0
                return d, vol
                
            rev_traj, rev_vol = process_series(rev_series)
            ni_traj, ni_vol = process_series(ni_series)
            opex_traj, opex_vol = process_series(opex_series)
            capex_traj, capex_vol = process_series(capex_series)
            
            nfp_traj, nfp_vol = {}, 0.0
            if not debt_series.empty and not cash_series.empty:
                common_dates = debt_series.index.intersection(cash_series.index)
                nfp_series = debt_series.loc[common_dates] - cash_series.loc[common_dates]
                nfp_traj, nfp_vol = process_series(nfp_series)
                
            sam_traj = {k: v * 5 for k, v in rev_traj.items()}
            tam_traj = {k: v * 4 for k, v in sam_traj.items()}
            
        except Exception as e:
            rev_traj, rev_vol = {}, 0.0
            ni_traj, ni_vol = {}, 0.0
            opex_traj, opex_vol = {}, 0.0
            capex_traj, capex_vol = {}, 0.0
            nfp_traj, nfp_vol = {}, 0.0
            sam_traj = {}
            tam_traj = {}
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
        bachelier_min_1y = None
        bachelier_max_1y = None
        if current_price and current_price > 0 and risk > 0:
            drift = exp_return - 0.5 * (risk ** 2)
            diffusion = 1.96 * risk # 1.96 standard deviations for 95% CI
            bs_min_1y = current_price * math.exp(drift - diffusion)
            bs_max_1y = current_price * math.exp(drift + diffusion)
            
            # Bachelier Model (Arithmetic Brownian Motion)
            expected_price_bachelier = current_price * (1 + exp_return)
            price_std_bachelier = current_price * risk
            bachelier_min_1y = expected_price_bachelier - 1.96 * price_std_bachelier
            bachelier_max_1y = expected_price_bachelier + 1.96 * price_std_bachelier
            
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
            
        # RL Backtest Accuracy (Sliding Window on Past Data)
        rl_accuracy = 0.0
        try:
            if len(ticker_hist) > 500:
                correct_predictions = 0
                total_windows = 0
                # Test at 5 different past points (sliding windows)
                for years_ago in range(1, 6):
                    idx = - (years_ago * 252)
                    if abs(idx) + 200 < len(ticker_hist):
                        past_slice = ticker_hist.iloc[:idx]
                        if len(past_slice) > 200:
                            past_ma50 = past_slice.rolling(50).mean().iloc[-1]
                            past_ma200 = past_slice.rolling(200).mean().iloc[-1]
                            
                            pred_buy = past_ma50 > past_ma200
                            future_price = ticker_hist.iloc[idx + 252] if (idx + 252 < 0) else ticker_hist.iloc[-1]
                            current_price_past = past_slice.iloc[-1]
                            actual_up = future_price > current_price_past
                            
                            if pred_buy == actual_up:
                                correct_predictions += 1
                            total_windows += 1
                if total_windows > 0:
                    rl_accuracy = (correct_predictions / total_windows) * 100
        except Exception:
            pass
            
        # TAM, SAM, SOM Estimation (in Billions)
        revenue = ticker_info.get("totalRevenue", 0)
        market_cap = ticker_info.get("marketCap", 0)
        som = revenue if revenue > 0 else (market_cap * 0.05 if market_cap else 0)
        sam = som * 5
        tam = sam * 4
        
        # Parameter Correlation
        highest_corr_ticker = "None"
        highest_corr_value = 0.0
        if ticker in corr_matrix.columns:
            corrs = corr_matrix[ticker].drop(ticker, errors='ignore')
            if not corrs.empty and not corrs.isna().all():
                highest_corr_ticker = str(corrs.idxmax())
                highest_corr_value = float(corrs.max())
        
        from news_correlation import calculate_news_impact
        news_data = calculate_news_impact(ticker, ticker_info.get("shortName", ticker))

        company_data = {
            "ticker": ticker,
            "name": ticker_info.get("shortName", ticker),
            "sector": ticker_info.get("sector", "Unknown"),
            "country": ticker_info.get("country", "Unknown"),
            "current_price": current_price,
            "historical_expected_return": exp_return,
            "volatility_risk": risk,
            "news_impact_score": news_data["impact_score"],
            "news_count": news_data["news_count"],
            "news_list": news_data.get("news_list", []),
            "sharpe_ratio": (exp_return - risk_free_rate) / risk if risk > 0 else 0,
            "analyst_target_price": target_mean_price,
            "analyst_expected_return": analyst_upside,
            "beta": beta,
            "capm_cost_of_equity": cost_of_equity,
            "bs_min_1y_estimation": bs_min_1y,
            "bs_max_1y_estimation": bs_max_1y,
            "bachelier_min_1y_estimation": bachelier_min_1y,
            "bachelier_max_1y_estimation": bachelier_max_1y,
            "sarima_1y_forecast": sarima_forecast,
            "rl_action": rl_action,
            "rl_confidence": rl_confidence,
            "rl_backtest_accuracy": rl_accuracy,
            "treynor_ratio": treynor_ratio,
            "sortino_ratio": sortino_ratio,
            "tam_b": tam / 1e9,
            "sam_b": sam / 1e9,
            "som_b": som / 1e9,
            "highest_corr_ticker": highest_corr_ticker,
            "highest_corr_value": highest_corr_value,
            "peg_ratio": ticker_info.get("pegRatio"),
            "return_on_equity": ticker_info.get("returnOnEquity"),
            "debt_to_equity": ticker_info.get("debtToEquity"),
            "profit_margin": ticker_info.get("profitMargins"),
            "operating_margin": ticker_info.get("operatingMargins"),
            "free_cash_flow": ticker_info.get("freeCashflow"),
            "total_debt": ticker_info.get("totalDebt"),
            "revenue_trajectory": rev_traj,
            "revenue_volatility": rev_vol,
            "net_income_trajectory": ni_traj,
            "net_income_volatility": ni_vol,
            "opex_trajectory": opex_traj,
            "opex_volatility": opex_vol,
            "capex_trajectory": capex_traj,
            "capex_volatility": capex_vol,
            "net_financial_position_trajectory": nfp_traj,
            "net_financial_position_volatility": nfp_vol,
            "sam_trajectory": sam_traj,
            "tam_trajectory": tam_traj,
            "last_updated": datetime.datetime.utcnow().isoformat()
        }
        results.append(company_data)
        
        try:
            mongo_url = os.getenv("MONGO_URL", "mongodb://mongo:27017")
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
            db_name = "investment_tools"
            if "/" in mongo_url.split("mongodb://")[-1]:
                db = client.get_default_database()
            else:
                db = client.get_database(db_name)
            
            db.companies_info.update_one({"ticker": ticker}, {"$set": company_data}, upsert=True)
        except Exception as e:
            print(f"Failed to store {ticker} in MongoDB: {e}")

    
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

class ChatRequest(BaseModel):
    prompt: str
    context: list = []

@app.post("/api/chat")
def chat_with_llm(request: ChatRequest):
    """Local LLM Chat endpoint using llama-cpp-python for financial queries."""
    try:
        import bleach
        # SECURITY: Sanitize the user input before passing it to the backend model
        clean_prompt = bleach.clean(request.prompt)
        
        # Build prompt with context
        context_str = ""
        if request.context:
            import json
            # Filter context to essential fields to prevent exceeding LLM context window limit
            essential_keys = ["ticker", "name", "current_price", "sharpe_ratio", "news_impact_score", "analyst_target_price", "rl_action", "tam_b", "peg_ratio", "revenue_trajectory", "revenue_volatility", "net_income_trajectory", "net_income_volatility", "opex_trajectory", "opex_volatility", "capex_trajectory", "capex_volatility", "net_financial_position_trajectory", "net_financial_position_volatility", "sam_trajectory", "tam_trajectory"]
            filtered_context = [{k: item[k] for k in essential_keys if k in item} for item in request.context[:5]]
            context_json = json.dumps(filtered_context)
            # Log the full JSON to the backend console for debugging (unbuffered)
            print(f"--- INCOMING CONTEXT JSON ---\n{context_json}\n-----------------------------", flush=True)
            
            context_str = f"Recent Quantitative Study Results (Top Assets JSON Data):\n{context_json}\n"
        
        # System prompt with platform awareness
        system_prompt = (
            "You are a Local LLM built into an advanced Investment Tools platform. "
            "You are deeply integrated with the platform's API which fetches live financial data, fundamental KPIs, and global stock lists (like the S&P 500) directly from the internet. "
            "You can provide information regarding a specific company or domain, summarize complex financial data, and extract valuable internet-fetched insights from the provided context."
        )
        
        # TinyLlama Chat Format
        full_prompt = f"<|system|>\n{system_prompt}</s>\n<|user|>\n{context_str}\nQuestion: {clean_prompt}</s>\n<|assistant|>\n"
        
        try:
            from llama_cpp import Llama
            import os
            model_path = os.path.join(os.path.dirname(__file__), "models", "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
            if not os.path.exists(model_path):
                return {"error": "Local LLM model is currently downloading or not found. Please try again in a few minutes."}
            
            global _llm
            if '_llm' not in globals():
                _llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)
                
            output = _llm(full_prompt, max_tokens=200, stop=["<|user|>", "</s>"], echo=False)
            response_text = output['choices'][0]['text'].strip()
            
            # SECURITY: Sanitize the model output before sending to frontend
            clean_response = bleach.clean(response_text)
            return {"response": clean_response}
            
        except ImportError:
            return {"error": "llama-cpp-python library is not installed yet."}
    except Exception as e:
        return {"error": f"LLM Error: {str(e)}"}

class BSRequest(BaseModel):
    S: float
    K: float
    T: float
    r: float
    sigma: float

@app.post("/api/black-scholes")
def compute_black_scholes(req: BSRequest):
    from scipy.stats import norm
    import math
    if req.T <= 0:
        return {
            "call_price": max(0.0, req.S - req.K),
            "put_price": max(0.0, req.K - req.S)
        }
    
    d1 = (math.log(req.S / req.K) + (req.r + 0.5 * req.sigma**2) * req.T) / (req.sigma * math.sqrt(req.T))
    d2 = d1 - req.sigma * math.sqrt(req.T)
    
    call_price = req.S * norm.cdf(d1) - req.K * math.exp(-req.r * req.T) * norm.cdf(d2)
    put_price = req.K * math.exp(-req.r * req.T) * norm.cdf(-d2) - req.S * norm.cdf(-d1)
    
    return {
        "call_price": call_price,
        "put_price": put_price
    }

