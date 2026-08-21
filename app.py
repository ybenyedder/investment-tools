from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
import numpy as np
import pandas as pd
import uvicorn
import os
import math
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static directory for frontend
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def index():
    """Serve the estimator UI at the root (was a 404 before)."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/version")
def version():
    return {"version": "1.0.0", "service": "sb-estimator"}

class EstimateRequest(BaseModel):
    initial_price: float = Field(default=100.0, gt=0)
    target_price: float = Field(default=110.0, gt=0)
    volatility: float = Field(default=0.2, gt=0, le=5.0)
    epsilon: float = Field(default=5.0, gt=0, le=1000.0)
    steps: int = Field(default=100, ge=10, le=1000)
    num_paths: int = Field(default=5, ge=1, le=50)
    algorithm: str = "pure_sb"

    @field_validator("algorithm")
    @classmethod
    def check_algorithm(cls, v):
        allowed = {"pure_sb", "kalman", "hybrid"}
        if v not in allowed:
            raise ValueError(f"algorithm must be one of {sorted(allowed)}")
        return v

class CalibrateRequest(BaseModel):
    prices: list[float] = Field(min_length=3)
    window: int = Field(default=20, ge=2, le=500)
    steps_ahead: int = Field(default=100, ge=1, le=2520)

    @field_validator("prices")
    @classmethod
    def check_prices(cls, v):
        if any(p is None or not math.isfinite(p) or p <= 0 for p in v):
            raise ValueError("all prices must be positive, finite numbers (log-space requires p > 0)")
        return v

def sinkhorn_knopp(a, b, C, epsilon, max_iter=1000, tol=1e-9):
    # Log-domain Sinkhorn to prevent numerical underflow
    log_a = np.log(a + 1e-15)
    log_b = np.log(b + 1e-15)
    f = np.zeros_like(a)
    g = np.zeros_like(b)
    
    for i in range(max_iter):
        f_prev = f.copy()
        
        arg_g = (f[:, None] - C) / epsilon
        max_g = np.max(arg_g, axis=0)
        lse_g = max_g + np.log(np.sum(np.exp(arg_g - max_g), axis=0) + 1e-15)
        g = epsilon * log_b - epsilon * lse_g
        
        arg_f = (g[None, :] - C) / epsilon
        max_f = np.max(arg_f, axis=1)
        lse_f = max_f + np.log(np.sum(np.exp(arg_f - max_f), axis=1) + 1e-15)
        f = epsilon * log_a - epsilon * lse_f
        
        if np.max(np.abs(f - f_prev)) < tol:
            break
            
    P = np.exp((f[:, None] + g[None, :] - C) / epsilon)
    return P

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
@limiter.limit("10/minute")
def run_estimation(req: EstimateRequest, request: Request):
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
        
    # Pre-sample target states for all paths
    target_indices = np.random.choice(len(states), size=req.num_paths, p=cond_prob)
    log_XT_all = states[target_indices][:, np.newaxis] # Shape: (num_paths, 1)
    
    t = np.linspace(0, 1, req.steps)
    dt = 1.0 / req.steps
    
    # Pre-generate Brownian bridges for all paths
    W = np.random.normal(0, np.sqrt(dt), (req.num_paths, req.steps))
    W[:, 0] = 0
    W = np.cumsum(W, axis=1)
    W -= t * W[:, -1:] # Broadcast shape (req.steps,) and (num_paths, 1)
    
    if req.algorithm == "pure_sb":
        # Pure Stochastic Transport (Schrödinger Bridge with GBM prior)
        log_path = log_init + t * (log_XT_all - log_init) + sigma * W
        
    elif req.algorithm == "kalman":
        # Kalman-like Method vectorized
        avg_drift = (np.log(req.target_price) - log_init) / req.steps
        
        drift_shocks = np.random.normal(0, (req.volatility/req.steps)*0.2, (req.num_paths, req.steps))
        drift_shocks[:, 0] = avg_drift
        drifts = np.cumsum(drift_shocks, axis=1)
        
        price_shocks = np.random.normal(0, req.volatility/np.sqrt(req.steps), (req.num_paths, req.steps))
        price_shocks[:, 0] = 0
        
        # log_p[t] = log_p[t-1] + drift[t] + shock[t]
        log_path_increments = drifts[:, 1:] + price_shocks[:, 1:]
        log_path = log_init + np.cumsum(log_path_increments, axis=1)
        log_path = np.column_stack((np.full((req.num_paths, 1), log_init), log_path))
        
    elif req.algorithm == "hybrid":
        # Hybrid Method vectorized
        avg_drift = (log_XT_all - log_init) / req.steps
        
        drift_shocks = np.random.normal(0, (req.volatility/req.steps)*0.5, (req.num_paths, req.steps))
        drift_shocks[:, 0] = avg_drift.flatten()
        drifts = np.cumsum(drift_shocks, axis=1)
        
        prior_path = log_init + np.cumsum(drifts[:, 1:], axis=1)
        prior_path = np.column_stack((np.full((req.num_paths, 1), log_init), prior_path))
        
        correction = t * (log_XT_all - prior_path[:, -1:])
        log_path = prior_path + correction + (sigma * 0.5) * W
    else:
        # Fallback
        log_path = log_init + t * (log_XT_all - log_init) + sigma * W
        
    # Exponentiate to get real prices
    path_matrix = np.exp(log_path)
    paths = path_matrix.tolist()
    final_prices = path_matrix[:, -1].tolist()
    avg_path = np.mean(path_matrix, axis=0)
    
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

def kalman_filter_price(prices, Q_var, R_var):
    # State: [log_price, log_drift]
    F = np.array([[1.0, 1.0], 
                  [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    
    Q = np.array([[Q_var, 0], 
                  [0, Q_var / 10.0]])
    R = np.array([[R_var]])
    
    x = np.array([[np.log(prices[0])], [0.0]])
    P = np.eye(2)
    
    filtered_prices = []
    
    for z in prices:
        # Predict
        x = F @ x
        P = F @ P @ F.T + Q
        
        # Update
        Z = np.array([[np.log(z)]])
        y = Z - H @ x
        S = H @ P @ H.T + R
        K = P @ H.T @ np.linalg.inv(S)
        
        x = x + K @ y
        P = (np.eye(2) - K @ H) @ P
        
        filtered_prices.append(np.exp(x[0, 0]))
        
    return x, P, filtered_prices
@app.post("/api/calibrate")
@limiter.limit("5/minute")
def run_calibration(req: CalibrateRequest, request: Request):
    # Need at least window+1 prices to produce window log-returns
    if len(req.prices) < req.window + 1:
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
    
    # Kalman Filter Anomaly Detection
    Q_var = (latest_vol / np.sqrt(252))**2  # Daily variance
    R_var = Q_var * 2.0  # Assume measurement noise is higher
    
    kf_state, _, _ = kalman_filter_price(prices, Q_var, R_var)
    
    # Project target price using KF robust state
    kf_log_price = kf_state[0, 0]
    kf_log_drift = kf_state[1, 0]
    kf_target_log = kf_log_price + kf_log_drift * req.steps_ahead
    kf_target_price = np.exp(kf_target_log)
    
    anomaly_detected = False
    anomaly_msg = ""
    deviation = abs(target_price - kf_target_price) / target_price
    
    if deviation > 0.15: # 15% deviation is considered a huge wrong estimation
        anomaly_detected = True
        anomaly_msg = f"ANOMALY DETECTED: The sliding window target ({round(target_price, 2)}) deviates by {round(deviation*100, 1)}% from the robust Kalman Filter accumulation projection ({round(kf_target_price, 2)})."
    
    return {
        "calibrated_volatility": round(float(latest_vol), 4),
        "calibrated_target_price": round(float(target_price), 2),
        "calibrated_epsilon": round(float(estimated_epsilon), 4),
        "current_price": round(float(current_price), 2),
        "rolling_volatility": [float(x) for x in rolling_vol],
        "rolling_drift": [float(x) for x in rolling_drift],
        "kf_target_price": round(float(kf_target_price), 2),
        "anomaly_detected": anomaly_detected,
        "anomaly_msg": anomaly_msg
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
