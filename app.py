from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import numpy as np
import pandas as pd
import uvicorn
import os
import math

app = FastAPI()

# Mount static directory for frontend
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

class EstimateRequest(BaseModel):
    initial_price: float = 100.0
    target_price: float = 110.0
    volatility: float = 0.2
    epsilon: float = 5.0
    steps: int = 100
    num_paths: int = 5

class CalibrateRequest(BaseModel):
    prices: list[float]
    window: int = 20
    steps_ahead: int = 100

def sinkhorn_knopp(a, b, C, epsilon, max_iter=1000, tol=1e-9):
    # Stabilized Sinkhorn
    K = np.exp(-C / epsilon)
    u = np.ones_like(a)
    v = np.ones_like(b)
    for _ in range(max_iter):
        u_prev = u.copy()
        v = b / (np.dot(K.T, u) + 1e-15)
        u = a / (np.dot(K, v) + 1e-15)
        if np.max(np.abs(u - u_prev)) < tol:
            break
    return np.diag(u) @ K @ np.diag(v)

def compute_rsi(data, window=14):
    diff = np.diff(data)
    gain = np.maximum(diff, 0)
    loss = np.maximum(-diff, 0)
    avg_gain = np.convolve(gain, np.ones(window)/window, mode='valid')
    avg_loss = np.convolve(loss, np.ones(window)/window, mode='valid')
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    pad = np.full(len(data) - len(rsi), np.nan)
    return np.concatenate([pad, rsi])

def compute_macd(data, slow=26, fast=12, signal=9):
    df = pd.DataFrame({'close': data})
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line.values, signal_line.values

@app.post("/api/estimate")
def estimate(req: EstimateRequest):
    # 1. Discretize state space in log-price (Geometric Brownian Motion prior)
    log_init = np.log(req.initial_price)
    log_target = np.log(req.target_price)
    
    # We span 3 standard deviations around the initial and target prices
    states = np.linspace(log_init - req.volatility * 3, log_target + req.volatility * 3, 50)
    
    # Initial distribution (sharp peak at log initial price)
    a = np.exp(-0.5 * ((states - log_init) / 0.05)**2)
    a /= a.sum()
    
    # Target distribution (Gaussian centered at log target price)
    b = np.exp(-0.5 * ((states - log_target) / req.volatility)**2)
    b /= b.sum()
    
    # Cost matrix in log-space (matches GBM prior)
    X, Y = np.meshgrid(states, states)
    C = (X - Y)**2
    
    # Compute Transport Plan (Schrodinger Bridge transition matrix)
    P = sinkhorn_knopp(a, b, C, req.epsilon)
    
    # Conditional probability P(X_T | X_0 = log_init)
    start_idx = np.argmin(np.abs(states - log_init))
    cond_prob = P[start_idx, :] / (P[start_idx, :].sum() + 1e-15)
    
    # Fallback if conditional probability is entirely zero
    if cond_prob.sum() == 0:
        cond_prob = b
        
    # The true diffusion coefficient (sigma) is derived from the entropic parameter epsilon
    # For cost C = (X-Y)^2, the variance of the prior is epsilon/2 over T=1.
    sigma = np.sqrt(req.epsilon / 2.0)
        
    paths = []
    final_prices = []
    for _ in range(req.num_paths):
        # Sample target state in log-space
        target_idx = np.random.choice(len(states), p=cond_prob)
        log_XT = states[target_idx]
        
        # Simulate Brownian bridge in log-space (Exact Schrödinger Bridge for GBM prior)
        t = np.linspace(0, 1, req.steps)
        dt = 1.0 / req.steps
        W = np.random.normal(0, np.sqrt(dt), req.steps)
        W[0] = 0
        W = np.cumsum(W)
        W -= t * W[-1] # standard brownian bridge
        
        # SDE path: X_t = x(1-t) + yt + sigma * W_t
        log_path = log_init + t * (log_XT - log_init) + sigma * W
        
        # Exponentiate to get real prices
        path = np.exp(log_path)
        
        paths.append(path.tolist())
        final_prices.append(path[-1])
        
    avg_path = np.mean(paths, axis=0)
    
    # Technical Indicators on average path
    rsi = compute_rsi(avg_path)
    macd, macd_signal = compute_macd(avg_path)
    
    # Fundamental Estimation at T
    mean_final_price = float(np.mean(final_prices))
    shares = 10_000_000
    
    # Stochastic fundamental estimates related to price
    per = max(5.0, np.random.normal(15, 3)) # P/E ratio
    eps = mean_final_price / per
    net_income = eps * shares
    
    roe = np.random.normal(0.15, 0.05) # 15% average ROE
    
    ebitda = net_income + np.random.normal(net_income * 0.4, net_income * 0.1) # Rough EBITDA estimate
    
    # Handle NaN values for JSON serialization
    clean_rsi = [x if not math.isnan(x) else None for x in rsi]
    clean_macd = [x if not math.isnan(x) else None for x in macd]
    clean_signal = [x if not math.isnan(x) else None for x in macd_signal]
    
    latest_rsi = clean_rsi[-1] if clean_rsi[-1] is not None else 50
    latest_macd = clean_macd[-1] if clean_macd[-1] is not None else 0
    
    return {
        "paths": paths,
        "metrics": {
            "mean_final_price": round(mean_final_price, 2),
            "estimated_per": round(per, 2),
            "estimated_roe": round(roe * 100, 2), # percentage
            "estimated_ebitda": round(ebitda, 2),
            "latest_rsi": round(latest_rsi, 2),
            "latest_macd": round(latest_macd, 2)
        },
        "indicators": {
            "rsi": clean_rsi,
            "macd": clean_macd,
            "macd_signal": clean_signal
        }
    }

@app.post("/api/calibrate")
def calibrate(req: CalibrateRequest):
    if len(req.prices) < req.window:
        return {"error": "Not enough data for the sliding window."}
        
    prices = np.array(req.prices)
    # Calculate log returns
    log_returns = np.diff(np.log(prices))
    
    rolling_vol = []
    rolling_drift = []
    
    # Sliding window
    for i in range(len(log_returns) - req.window + 1):
        window_returns = log_returns[i:i+req.window]
        # Annualized volatility (assuming daily data, 252 days)
        vol = np.std(window_returns) * np.sqrt(252)
        drift = np.mean(window_returns) * 252
        rolling_vol.append(vol)
        rolling_drift.append(drift)
        
    latest_vol = rolling_vol[-1]
    latest_drift = rolling_drift[-1]
    current_price = prices[-1]
    
    # Estimate Target Price based on drift
    target_price = current_price * np.exp(latest_drift * (req.steps_ahead / 252))
    
    # Estimate Entropy: epsilon = 2 * sigma^2 over the period
    period_variance = (latest_vol ** 2) * (req.steps_ahead / 252)
    estimated_epsilon = 2.0 * period_variance
    
    return {
        "calibrated_volatility": round(float(latest_vol), 4),
        "calibrated_target_price": round(float(target_price), 2),
        "calibrated_epsilon": round(float(estimated_epsilon), 4),
        "current_price": round(float(current_price), 2),
        "rolling_volatility": [float(x) for x in rolling_vol],
        "rolling_drift": [float(x) for x in rolling_drift]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
