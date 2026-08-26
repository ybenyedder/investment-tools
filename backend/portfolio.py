"""User authentication and virtual stock portfolio (paper trading).

Design notes:
- Zero extra dependencies: scrypt password hashing and HMAC-signed tokens
  come from the Python standard library; storage is SQLite.
- The database lives in PORTFOLIO_DB (defaults to backend/data/portfolio.db
  next to this file). In Docker it is mounted on a host volume so data
  survives rebuilds.
- Every user starts with a virtual cash balance (INITIAL_CASH) used to
  "buy" shares at live market prices fetched from yfinance.

All monetary amounts are in USD.
"""

import base64
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

INITIAL_CASH = 100_000.0
TOKEN_TTL_SECONDS = 30 * 24 * 3600  # 30 days
RISK_FREE_RATE = 0.04
_WRITE_LOCK = threading.Lock()
_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _db_path() -> str:
    path = os.getenv("PORTFOLIO_DB") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "portfolio.db"
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


@contextmanager
def _connect():
    conn = sqlite3.connect(_db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                cash REAL NOT NULL DEFAULT 100000.0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ticker TEXT NOT NULL,
                side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                fees REAL NOT NULL DEFAULT 0,
                ts TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id, ts);
            CREATE TABLE IF NOT EXISTS ticker_meta (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                sector TEXT NOT NULL DEFAULT '',
                updated_at REAL NOT NULL
            );
            """
        )
        conn.commit()


def reset_db_for_tests():
    """Drop and recreate all tables (used by the test suite on temp DBs)."""
    with _connect() as conn:
        conn.executescript(
            "DROP TABLE IF EXISTS transactions;"
            "DROP TABLE IF EXISTS users;"
            "DROP TABLE IF EXISTS ticker_meta;"
        )
        conn.commit()
    init_db()


# ---------------------------------------------------------------------------
# Passwords & tokens
# ---------------------------------------------------------------------------

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), dklen=32,
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _secret() -> bytes:
    env = os.getenv("PORTFOLIO_SECRET")
    if env:
        return env.encode()
    # No env secret: generate one and persist it next to the DB so tokens
    # stay valid across restarts.
    key_path = os.path.join(os.path.dirname(_db_path()), "secret.key")
    try:
        with open(key_path, "rb") as f:
            return f.read().strip()
    except FileNotFoundError:
        key = secrets.token_hex(32).encode()
        with open(key_path, "wb") as f:
            f.write(key)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        return key


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def create_token(user_id: str) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_token(token: str):
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64url_decode(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("uid")
    except Exception:
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> sqlite3.Row:
    """FastAPI dependency: resolves the bearer token to a user row or raises 401."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    uid = verify_token(credentials.credentials)
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    with _connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


# ---------------------------------------------------------------------------
# Market data helpers (patched in tests)
# ---------------------------------------------------------------------------

def get_current_prices(tickers) -> dict:
    """Latest closing prices for a list of tickers (dict, ticker -> price)."""
    tickers = [t.upper().strip() for t in tickers if t and t.strip()]
    if not tickers:
        return {}
    try:
        data = yf.download(list(tickers), period="5d", progress=False, auto_adjust=True)["Close"]
        if isinstance(data, pd.Series):
            data = data.to_frame(name=tickers[0])
        data = data.ffill()
        latest = data.iloc[-1]
        return {t: float(latest[t]) for t in data.columns if pd.notna(latest[t])}
    except Exception:
        return {}


def get_market_price(ticker: str) -> float:
    """Current market price for a single ticker. Raises 400 on failure."""
    ticker = ticker.upper().strip()
    try:
        price = yf.Ticker(ticker).fast_info.last_price
        if price and math.isfinite(float(price)) and float(price) > 0:
            return float(price)
    except Exception:
        pass
    prices = get_current_prices([ticker])
    if ticker in prices:
        return prices[ticker]
    raise HTTPException(status_code=400, detail=f"Could not fetch a market price for '{ticker}'. Verify the ticker.")


def fetch_history(tickers, period: str = "3y") -> pd.DataFrame:
    """Historical adjusted closes (patched by the test suite)."""
    return yf.download(list(tickers), period=period, progress=False, auto_adjust=True)["Close"]


_META_TTL = 24 * 3600  # cache company names/sectors for one day


def get_tickers_meta(tickers) -> dict:
    """{ticker: {name, sector}} with a one-day local cache."""
    tickers = [t.upper().strip() for t in tickers if t and t.strip()]
    now = time.time()
    out, missing = {}, []
    with _connect() as conn:
        for t in tickers:
            row = conn.execute("SELECT * FROM ticker_meta WHERE ticker = ?", (t,)).fetchone()
            if row and now - row["updated_at"] < _META_TTL:
                out[t] = {"name": row["name"], "sector": row["sector"]}
            else:
                missing.append(t)
    for t in missing:
        name, sector = t, "Unknown"
        try:
            info = yf.Ticker(t).info or {}
            name = info.get("shortName") or info.get("longName") or t
            if info.get("quoteType") == "ETF":
                sector = "ETF / Fonds"
            else:
                sector = info.get("sector") or "Unknown"
        except Exception:
            pass
        out[t] = {"name": name, "sector": sector}
        with _WRITE_LOCK, _connect() as conn:
            conn.execute(
                "INSERT INTO ticker_meta (ticker, name, sector, updated_at) VALUES (?,?,?,?) "
                "ON CONFLICT(ticker) DO UPDATE SET name=excluded.name, sector=excluded.sector, updated_at=excluded.updated_at",
                (t, name, sector, now),
            )
            conn.commit()
    return out


# ---------------------------------------------------------------------------
# Portfolio computation
# ---------------------------------------------------------------------------

def _positions_from_transactions(rows) -> dict:
    """Aggregate transactions into positions using the average-cost method."""
    positions = {}
    realized_pnl = 0.0
    for r in rows:
        t = r["ticker"].upper()
        pos = positions.setdefault(t, {"quantity": 0.0, "avg_cost": 0.0, "invested": 0.0})
        qty, price = float(r["quantity"]), float(r["price"])
        fees = float(r["fees"] or 0.0)
        if r["side"] == "BUY":
            pos["invested"] += qty * price + fees
            pos["quantity"] += qty
            pos["avg_cost"] = pos["invested"] / pos["quantity"] if pos["quantity"] > 0 else 0.0
        else:  # SELL
            sold = min(qty, pos["quantity"])
            realized_pnl += sold * (price - pos["avg_cost"]) - fees
            pos["invested"] -= sold * pos["avg_cost"]
            pos["quantity"] -= qty
            if pos["quantity"] <= 1e-9:
                pos["quantity"], pos["invested"], pos["avg_cost"] = 0.0, 0.0, 0.0
    return {t: p for t, p in positions.items() if p["quantity"] > 1e-9}, realized_pnl


def build_portfolio_view(user) -> dict:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY ts ASC, id ASC", (user["id"],)
        ).fetchall()
    positions, realized_pnl = _positions_from_transactions(rows)
    tickers = list(positions.keys())
    prices = get_current_prices(tickers)
    meta = get_tickers_meta(tickers)

    cash = float(user["cash"])
    out_positions = []
    for t, p in positions.items():
        price = prices.get(t, p["avg_cost"])
        value = p["quantity"] * price
        cost_basis = p["quantity"] * p["avg_cost"]
        pnl = value - cost_basis
        out_positions.append({
            "ticker": t,
            "name": meta.get(t, {}).get("name", t),
            "sector": meta.get(t, {}).get("sector", "Unknown"),
            "quantity": round(p["quantity"], 6),
            "avg_cost": round(p["avg_cost"], 2),
            "current_price": round(price, 2),
            "value": round(value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / cost_basis * 100, 2) if cost_basis > 0 else 0.0,
            "weight_pct": 0.0,  # filled below
        })

    invested = sum(p["value"] for p in out_positions)
    total_value = invested + cash
    for p in out_positions:
        p["weight_pct"] = round(p["value"] / total_value * 100, 2) if total_value > 0 else 0.0

    cost_total = sum(p["quantity"] * p["avg_cost"] for p in out_positions)
    unrealized_pnl = invested - cost_total
    return {
        "cash": round(cash, 2),
        "invested": round(invested, 2),
        "total_value": round(total_value, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "realized_pnl": round(realized_pnl, 2),
        "total_pnl": round(unrealized_pnl + realized_pnl, 2),
        "initial_cash": INITIAL_CASH,
        "total_return_pct": round((total_value - INITIAL_CASH) / INITIAL_CASH * 100, 2),
        "positions": out_positions,
    }


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=80)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class TradeRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    side: str = Field(pattern="^(buy|sell|BUY|SELL)$")
    quantity: float = Field(gt=0, le=1_000_000)
    price: float | None = Field(default=None, gt=0)  # optional override (paper price)
    fees: float = Field(default=0.0, ge=0)


class ProjectionRequest(BaseModel):
    years: float = Field(default=5, gt=0, le=30)
    simulations: int = Field(default=500, ge=50, le=2000)


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Handlers (registered on the main app)
# ---------------------------------------------------------------------------

def register_user(req: RegisterRequest):
    email = req.email.strip().lower()
    # EmailStr already validates; keep a defensive check for test transports.
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Invalid email address")
    init_db()
    user_id = secrets.token_hex(16)
    try:
        with _WRITE_LOCK, _connect() as conn:
            conn.execute(
                "INSERT INTO users (id, email, name, password_hash, cash, created_at) VALUES (?,?,?,?,?,?)",
                (user_id, email, req.name.strip() or email.split("@")[0], hash_password(req.password), INITIAL_CASH, _utcnow_iso()),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="An account already exists for this email")
    return {"token": create_token(user_id), "user": {"id": user_id, "email": email}}


def login_user(req: LoginRequest):
    init_db()
    with _connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (req.email.strip().lower(),)).fetchone()
    if user is None or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"token": create_token(user["id"]), "user": {"id": user["id"], "email": user["email"]}}


def me(user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "cash": round(float(user["cash"]), 2),
        "created_at": user["created_at"],
    }


def execute_trade(req: TradeRequest, user=Depends(get_current_user)):
    init_db()
    ticker = req.ticker.upper().strip()
    side = req.side.upper()
    price = float(req.price) if req.price is not None else get_market_price(ticker)
    qty = float(req.quantity)
    cost = qty * price + req.fees

    with _WRITE_LOCK, _connect() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
        rows = conn.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY ts ASC, id ASC", (user["id"],)
        ).fetchall()
        positions, _ = _positions_from_transactions(rows)
        held = positions.get(ticker, {}).get("quantity", 0.0)

        if side == "BUY":
            if cost > float(user["cash"]) + 1e-6:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient cash: order costs ${cost:,.2f} but you have ${float(user['cash']):,.2f}",
                )
            new_cash = float(user["cash"]) - cost
        else:
            if qty > held + 1e-9:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient shares: you hold {held:,.4f} of {ticker} but tried to sell {qty:,.4f}",
                )
            new_cash = float(user["cash"]) + qty * price - req.fees

        conn.execute(
            "INSERT INTO transactions (user_id, ticker, side, quantity, price, fees, ts) VALUES (?,?,?,?,?,?,?)",
            (user["id"], ticker, side, qty, price, req.fees, _utcnow_iso()),
        )
        conn.execute("UPDATE users SET cash = ? WHERE id = ?", (new_cash, user["id"]))
        conn.commit()

    return {
        "status": "ok",
        "side": side,
        "ticker": ticker,
        "quantity": qty,
        "price": round(price, 2),
        "fees": req.fees,
        "cash_after": round(new_cash, 2),
    }


def trade_history(user=Depends(get_current_user)):
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ticker, side, quantity, price, fees, ts FROM transactions WHERE user_id = ? ORDER BY ts DESC, id DESC LIMIT 200",
            (user["id"],),
        ).fetchall()
    return {"transactions": [dict(r) for r in rows]}


def reset_portfolio(user=Depends(get_current_user)):
    init_db()
    with _WRITE_LOCK, _connect() as conn:
        conn.execute("DELETE FROM transactions WHERE user_id = ?", (user["id"],))
        conn.execute("UPDATE users SET cash = ? WHERE id = ?", (INITIAL_CASH, user["id"]))
        conn.commit()
    return {"status": "ok", "cash": INITIAL_CASH}


# ---------------------------------------------------------------------------
# Monte Carlo projection
# ---------------------------------------------------------------------------

def compute_projection(req: ProjectionRequest, user=Depends(get_current_user)):
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY ts ASC, id ASC", (user["id"],)
        ).fetchall()
    positions, _ = _positions_from_transactions(rows)
    if not positions:
        raise HTTPException(status_code=400, detail="Your portfolio is empty — buy some shares first")

    tickers = list(positions.keys())
    cash = float(user["cash"])
    prices = get_current_prices(tickers)
    values = np.array([positions[t]["quantity"] * prices.get(t, positions[t]["avg_cost"]) for t in tickers])
    invested = float(values.sum())
    total_value = invested + cash

    hist = fetch_history(tickers, period="3y")
    if isinstance(hist, pd.Series):
        hist = hist.to_frame(name=tickers[0])
    # Align columns to the tickers order and keep only assets with real history
    hist = hist[[t for t in tickers if t in hist.columns]]
    usable = list(hist.columns)
    if usable:
        keep = [i for i, t in enumerate(tickers) if t in usable]
        tickers = usable
        values = values[keep]
        invested = float(values.sum())
    hist = hist.dropna(how="all").ffill().dropna(how="any")
    if len(hist) < 60:
        raise HTTPException(status_code=400, detail="Not enough historical data to run a projection")

    rets = np.log(hist / hist.shift(1)).dropna()
    mu_d = rets.mean().values               # daily log-return mean per asset
    cov_d = rets.cov().values               # daily log-return covariance
    weights = values / invested             # portfolio weights (invested part)

    port_mu_d = float(weights @ mu_d)
    port_var_d = float(weights @ cov_d @ weights)

    n_steps = int(req.years * 252)
    n_sims = req.simulations
    rng = np.random.default_rng(42)
    # Correlated shocks via Cholesky (with jitter for near-singular matrices)
    cov = cov_d + np.eye(len(tickers)) * 1e-10
    try:
        chol = np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        chol = np.eye(len(tickers))

    shocks = rng.standard_normal((n_sims, n_steps, len(tickers))) @ chol.T  # (sims, steps, assets)
    asset_logrets = mu_d + shocks
    port_logret = asset_logrets @ weights  # daily-rebalanced portfolio log-return
    # Cash stays constant; only the invested part compounds.
    paths_value = invested * np.exp(np.cumsum(port_logret, axis=1)) + cash

    # Downsample to <= 80 points for the chart
    step_idx = np.linspace(0, n_steps - 1, min(80, n_steps)).astype(int)
    sampled = paths_value[:, step_idx]
    p10 = np.percentile(sampled, 10, axis=0)
    p50 = np.percentile(sampled, 50, axis=0)
    p90 = np.percentile(sampled, 90, axis=0)
    months = (step_idx / 252 * 12).round(1).tolist()

    finals = paths_value[:, -1]
    pcts = np.percentile(finals, [5, 25, 50, 75, 95])
    prob_loss = float((finals < total_value).mean() * 100)
    med = float(pcts[2])
    cagr = ((med / total_value) ** (1 / req.years) - 1) * 100 if total_value > 0 else 0.0

    ann_vol = math.sqrt(port_var_d * 252) * 100
    ann_ret = (math.exp(port_mu_d * 252) - 1) * 100
    ann_sharpe = (math.exp(port_mu_d * 252) - 1 - RISK_FREE_RATE) / math.sqrt(port_var_d * 252) if port_var_d > 0 else 0.0

    per_asset = []
    for i, t in enumerate(tickers):
        a_mu = math.exp(mu_d[i] * 252) - 1
        a_vol = math.sqrt(cov_d[i, i] * 252)
        per_asset.append({
            "ticker": t,
            "weight_pct": round(float(weights[i]) * 100, 1),
            "expected_annual_return_pct": round(a_mu * 100, 2),
            "annual_volatility_pct": round(a_vol * 100, 2),
            "range_1y_95": [
                round(prices.get(t, positions[t]["avg_cost"]) * math.exp(a_mu - 1.96 * a_vol), 2),
                round(prices.get(t, positions[t]["avg_cost"]) * math.exp(a_mu + 1.96 * a_vol), 2),
            ],
        })

    return {
        "years": req.years,
        "simulations": n_sims,
        "current_value": round(total_value, 2),
        "expected_annual_return_pct": round(ann_ret, 2),
        "annual_volatility_pct": round(ann_vol, 2),
        "sharpe_ratio": round(ann_sharpe, 2),
        "chart": {
            "months": months,
            "p10": [round(float(x), 2) for x in p10],
            "p50": [round(float(x), 2) for x in p50],
            "p90": [round(float(x), 2) for x in p90],
        },
        "final_distribution": {
            "p5": round(float(pcts[0]), 2),
            "p25": round(float(pcts[1]), 2),
            "median": round(float(pcts[2]), 2),
            "p75": round(float(pcts[3]), 2),
            "p95": round(float(pcts[4]), 2),
            "prob_loss_pct": round(prob_loss, 1),
            "median_cagr_pct": round(cagr, 2),
        },
        "per_asset": per_asset,
    }


# ---------------------------------------------------------------------------
# Advice engine (rule-based, no LLM required)
# ---------------------------------------------------------------------------

def compute_advice(user=Depends(get_current_user)):
    init_db()
    view = build_portfolio_view(user)
    positions = view["positions"]
    advice, score = [], 70  # neutral base score

    if not positions:
        return {
            "score": 0,
            "summary": "Votre portefeuille est vide. Commencez par acheter vos premières actions (bouton « Acheter » sur chaque société) — un ETF diversifié type SPY ou VT est un bon point de départ.",
            "advice": [{
                "type": "action",
                "title": "Premier investissement",
                "detail": "Avec 100 000 $ de cash virtuel, répartissez-vous entre 5 et 10 lignes de secteurs différents, ou démarrez avec un ETF mondial (VT, SPY) pour une diversification immédiate.",
            }],
        }

    tickers = [p["ticker"] for p in positions]

    # --- Concentration check
    top = max(positions, key=lambda p: p["value"])
    if top["weight_pct"] > 40:
        score -= 15
        advice.append({
            "type": "warning",
            "title": f"Concentration élevée sur {top['ticker']}",
            "detail": f"{top['name']} représente {top['weight_pct']}% de votre portefeuille. Au-delà de 25-30% par ligne, le risque idiosyncratique domine : envisagez de réduire la position.",
        })
    elif top["weight_pct"] > 25:
        score -= 5
        advice.append({
            "type": "info",
            "title": f"Position importante : {top['ticker']} ({top['weight_pct']}%)",
            "detail": "Poids supérieur à 25% : surveillez cette ligne, une chute isolée pèserait lourd sur la performance globale.",
        })
    else:
        score += 10

    # --- Sector diversification
    sectors = {}
    for p in positions:
        sectors[p["sector"]] = sectors.get(p["sector"], 0.0) + p["weight_pct"]
    top_sector, top_sector_w = max(sectors.items(), key=lambda kv: kv[1])
    if len(sectors) == 1 and len(positions) > 1:
        score -= 10
        advice.append({
            "type": "warning",
            "title": f"Portefeuille mono-secteur ({top_sector})",
            "detail": "Toutes vos lignes appartiennent au même secteur. Ajoutez des actifs d'autres secteurs (santé, énergie, consommation…) pour réduire le risque systélique sectoriel.",
        })
    elif top_sector_w > 50:
        score -= 5
        advice.append({
            "type": "info",
            "title": f"Exposition sectorielle forte : {top_sector} ({top_sector_w:.0f}%)",
            "detail": "Plus de la moitié du portefeuille est exposée à un seul secteur.",
        })
    else:
        score += 10

    # --- Cash management
    cash_pct = view["cash"] / view["total_value"] * 100 if view["total_value"] > 0 else 100
    if cash_pct > 40:
        score -= 5
        advice.append({
            "type": "info",
            "title": f"{cash_pct:.0f}% de liquidités inutilisées",
            "detail": "Votre cash virtuel ne rapporte rien. Soit c'est une position d'attente volontaire, soit investissez progressivement (DCA) pour réduire le risque de timing.",
        })
    elif cash_pct < 2:
        advice.append({
            "type": "info",
            "title": "Quasi plus de liquidités",
            "detail": "Vous êtes pleinement investi : aucune marge pour saisir une baisse ou corriger un tir. Garder 5-10% de cash est une discipline utile.",
        })
    else:
        score += 5

    # --- Risk & performance from history
    try:
        hist = fetch_history(tickers, period="1y")
        if isinstance(hist, pd.Series):
            hist = hist.to_frame(name=tickers[0])
        hist = hist.dropna(how="all").ffill()
        available = [t for t in tickers if t in hist.columns and hist[t].notna().sum() > 30]
        if available:
            year_ret = (hist[available].ffill().iloc[-1] / hist[available].dropna().iloc[0] - 1) * 100
            for t in available:
                r = float(year_ret[t])
                w = next(p["weight_pct"] for p in positions if p["ticker"] == t)
                if r < -25:
                    score -= 5
                    advice.append({
                        "type": "warning",
                        "title": f"{t} : {r:.0f}% sur 1 an",
                        "detail": f"Forte sous-performance. Revoyez la thèse d'investissement : s'agit-il d'un repli opportunité ou d'une dégradation fondamentale ?",
                    })
                elif r > 60 and w > 20:
                    advice.append({
                        "type": "action",
                        "title": f"{t} : {r:+.0f}% sur 1 an",
                        "detail": "Excellent rendement qui a fait gonfler le poids de la ligne. Encaisser une partie (sell partiel) rééquilibrerait le risque automatiquement.",
                    })
            best = year_ret.idxmax()
            advice.append({
                "type": "positive",
                "title": f"Meilleure performance 1 an : {best} ({float(year_ret[best]):+.1f}%)",
                "detail": "Vos gagnants financent vos pertes : laissez courir les tendances tout en plafonnant les poids.",
            })
    except Exception:
        pass

    # --- Portfolio-level risk
    try:
        proj = compute_projection(ProjectionRequest(years=1, simulations=200), user)
        vol = proj["annual_volatility_pct"]
        sharpe = proj["sharpe_ratio"]
        if vol > 35:
            score -= 10
            advice.append({
                "type": "warning",
                "title": f"Volatilité annuelle élevée : {vol:.0f}%",
                "detail": "Des variations de ±35% par an sont typiques des portefeuilles concentrés en tech/petites caps. Des ETF ou des secteurs défensifs réduiraient l'amplitude.",
            })
        else:
            score += 10
        if sharpe > 1:
            advice.append({
                "type": "positive",
                "title": f"Sharpe ratio de {sharpe:.2f}",
                "detail": "Excellent couple rendement/risque historique (Sharpe > 1).",
            })
        elif sharpe < 0:
            score -= 10
            advice.append({
                "type": "warning",
                "title": f"Sharpe ratio négatif ({sharpe:.2f})",
                "detail": "Le rendement attendu est sous le taux sans risque (4%) : la compensation au risque est insuffisante sur la base des données historiques.",
            })
    except HTTPException:
        pass

    # --- Diversification sizing
    if len(positions) < 5:
        score -= 5
        advice.append({
            "type": "info",
            "title": f"Portefeuille de {len(positions)} ligne(s)",
            "detail": "Entre 8 et 15 lignes de secteurs différents suffit à éliminer l'essentiel du risque spécifique.",
        })
    else:
        score += 5

    score = max(0, min(100, score))
    return {
        "score": score,
        "summary": _summary_text(score, view),
        "advice": advice,
        "sectors": [{"sector": s, "weight_pct": round(w, 1)} for s, w in sorted(sectors.items(), key=lambda kv: -kv[1])],
    }


def _summary_text(score: int, view: dict) -> str:
    pnl = view["total_pnl"]
    ret = view["total_return_pct"]
    trend = "en gain" if pnl >= 0 else "en perte"
    if score >= 75:
        qual = "bien structuré et diversifié"
    elif score >= 50:
        qual = "correct, avec des axes d'amélioration listés ci-dessous"
    else:
        qual = "fragile : suivez prioritairement les alertes ci-dessous"
    return (
        f"Portefeuille {trend} ({pnl:+,.2f} $, soit {ret:+.2f}% depuis l'origine) — {qual}. "
        f"Valeur totale : {view['total_value']:,.2f} $ dont {view['cash']:,.2f} $ de liquidités."
    )

def optimize_portfolio(user=Depends(get_current_user)):
    """Automated persona that optimizes the portfolio by liquidating underperforming assets and buying top ones."""
    init_db()
    view = build_portfolio_view(user)
    
    positions = view["positions"]
    
    actions_taken = []
    
    # 1. Sell underperformers (pnl_pct < -5.0)
    for p in positions:
        if p["pnl_pct"] < -5.0:
            try:
                req = TradeRequest(ticker=p["ticker"], side="SELL", quantity=p["quantity"])
                res = execute_trade(req, user)
                actions_taken.append(f"Vendu {p['quantity']} de {p['ticker']} (Stop loss)")
            except Exception as e:
                pass

    # Refetch cash after selling
    view = build_portfolio_view(user)
    cash = view["cash"]

    # 2. Reinvest cash in SPY or QQQ if abundant
    if cash > 1000:
        for ticker in ["QQQ", "SPY"]:
            try:
                price = get_market_price(ticker)
                qty = math.floor((cash * 0.4) / price)
                if qty > 0:
                    req = TradeRequest(ticker=ticker, side="BUY", quantity=qty)
                    res = execute_trade(req, user)
                    actions_taken.append(f"Acheté {qty} de {ticker} (Réinvestissement optimal)")
                    cash -= (qty * price)
            except Exception as e:
                pass
                
    if not actions_taken:
        actions_taken.append("Aucune optimisation nécessaire.")
        
    return {"status": "ok", "actions": actions_taken}
