"""Tests for auth + virtual portfolio + projection + advice endpoints."""
import math

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

import portfolio
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Isolate every test on a fresh database + fixed secret."""
    monkeypatch.setenv("PORTFOLIO_DB", str(tmp_path / "portfolio.db"))
    monkeypatch.setenv("PORTFOLIO_SECRET", "test-secret")
    portfolio.reset_db_for_tests()
    yield


def _register(email="alice@test.com", password="password123"):
    return client.post("/api/auth/register", json={"email": email, "password": password, "name": "Alice"})


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _fake_history(tickers, period="3y"):
    """Deterministic geometric random walk, ~2 years of daily data."""
    rng = np.random.default_rng(7)
    dates = pd.bdate_range(end="2026-08-19", periods=300)
    data = {}
    for t in tickers:
        rets = rng.normal(0.0005, 0.015, len(dates))
        data[t] = 100 * np.exp(np.cumsum(rets))
    return pd.DataFrame(data, index=dates)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_register_login_me(self):
        res = _register()
        assert res.status_code == 200
        token = res.json()["token"]
        assert token

        me = client.get("/api/auth/me", headers=_auth_headers(token))
        assert me.status_code == 200
        assert me.json()["email"] == "alice@test.com"
        assert me.json()["cash"] == 100000.0

    def test_register_duplicate_email(self):
        _register()
        res = _register()
        assert res.status_code == 409

    def test_register_short_password(self):
        res = _register(email="bob@test.com", password="short")
        assert res.status_code == 422

    def test_register_invalid_email(self):
        res = client.post("/api/auth/register", json={"email": "not-an-email", "password": "password123"})
        assert res.status_code == 422

    def test_login_wrong_password(self):
        _register()
        res = client.post("/api/auth/login", json={"email": "alice@test.com", "password": "wrongpass1"})
        assert res.status_code == 401

    def test_login_success(self):
        _register()
        res = client.post("/api/auth/login", json={"email": "alice@test.com", "password": "password123"})
        assert res.status_code == 200
        assert "token" in res.json()

    def test_invalid_token_rejected(self):
        me = client.get("/api/auth/me", headers=_auth_headers("abc.def"))
        assert me.status_code == 401

    def test_no_token_rejected(self):
        me = client.get("/api/auth/me")
        assert me.status_code == 401


# ---------------------------------------------------------------------------
# Trading
# ---------------------------------------------------------------------------

class TestTrading:
    def test_buy_at_explicit_price(self):
        token = _register().json()["token"]
        res = client.post("/api/portfolio/trade", json={
            "ticker": "AAPL", "side": "buy", "quantity": 10, "price": 150.0
        }, headers=_auth_headers(token))
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert body["cash_after"] == 100000.0 - 10 * 150.0

    def test_portfolio_view_math(self):
        token = _register().json()["token"]
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 10, "price": 100.0}, headers=_auth_headers(token))
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 10, "price": 120.0}, headers=_auth_headers(token))

        with patch.object(portfolio, "get_current_prices", return_value={"AAPL": 130.0}), \
             patch.object(portfolio, "get_tickers_meta", return_value={"AAPL": {"name": "Apple", "sector": "Technology"}}):
            view = client.get("/api/portfolio", headers=_auth_headers(token)).json()

        pos = view["positions"][0]
        assert pos["ticker"] == "AAPL"
        assert pos["quantity"] == 20
        assert pos["avg_cost"] == 110.0          # (10*100 + 10*120) / 20
        assert pos["current_price"] == 130.0
        assert pos["value"] == 2600.0
        assert pos["pnl"] == 400.0               # 20 * (130 - 110)
        assert view["cash"] == 100000.0 - 2200.0
        assert view["total_value"] == 97800.0 + 2600.0

    def test_buy_insufficient_cash(self):
        token = _register().json()["token"]
        res = client.post("/api/portfolio/trade", json={
            "ticker": "BRK.A", "side": "buy", "quantity": 100, "price": 600000.0
        }, headers=_auth_headers(token))
        assert res.status_code == 400
        assert "Insufficient cash" in res.json()["detail"]

    def test_sell_more_than_held(self):
        token = _register().json()["token"]
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 5, "price": 100.0}, headers=_auth_headers(token))
        res = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "sell", "quantity": 10, "price": 110.0}, headers=_auth_headers(token))
        assert res.status_code == 400
        assert "Insufficient shares" in res.json()["detail"]

    def test_sell_reduces_position_and_credits_cash(self):
        token = _register().json()["token"]
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 10, "price": 100.0}, headers=_auth_headers(token))
        res = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "sell", "quantity": 4, "price": 150.0}, headers=_auth_headers(token))
        assert res.status_code == 200
        assert res.json()["cash_after"] == pytest.approx(100000.0 - 1000.0 + 4 * 150.0)

        view = client.get("/api/portfolio", headers=_auth_headers(token)).json()
        assert view["positions"][0]["quantity"] == 6

    def test_market_price_fetched_when_price_omitted(self):
        token = _register().json()["token"]
        with patch.object(portfolio, "get_market_price", return_value=200.0) as mock_price:
            res = client.post("/api/portfolio/trade", json={"ticker": "MSFT", "side": "buy", "quantity": 2}, headers=_auth_headers(token))
        assert res.status_code == 200
        assert mock_price.called
        assert res.json()["price"] == 200.0

    def test_trade_requires_auth(self):
        res = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 1, "price": 100})
        assert res.status_code == 401

    def test_history_endpoint(self):
        token = _register().json()["token"]
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 1, "price": 100.0}, headers=_auth_headers(token))
        res = client.get("/api/portfolio/history", headers=_auth_headers(token))
        assert res.status_code == 200
        txs = res.json()["transactions"]
        assert len(txs) == 1
        assert txs[0]["side"] == "BUY"

    def test_reset_portfolio(self):
        token = _register().json()["token"]
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 10, "price": 100.0}, headers=_auth_headers(token))
        res = client.post("/api/portfolio/reset", headers=_auth_headers(token))
        assert res.status_code == 200
        view = client.get("/api/portfolio", headers=_auth_headers(token)).json()
        assert view["positions"] == []
        assert view["cash"] == 100000.0


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------

class TestProjection:
    def test_projection_structure(self):
        token = _register().json()["token"]
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 100, "price": 150.0}, headers=_auth_headers(token))
        client.post("/api/portfolio/trade", json={"ticker": "MSFT", "side": "buy", "quantity": 50, "price": 300.0}, headers=_auth_headers(token))

        with patch.object(portfolio, "get_current_prices", return_value={"AAPL": 150.0, "MSFT": 300.0}), \
             patch.object(portfolio, "fetch_history", side_effect=_fake_history):
            res = client.post("/api/portfolio/projection", json={"years": 2, "simulations": 100}, headers=_auth_headers(token))

        assert res.status_code == 200
        data = res.json()
        assert data["current_value"] == 100000.0 - 15000.0 - 15000.0 + 15000.0 + 15000.0
        chart = data["chart"]
        assert len(chart["p10"]) == len(chart["p50"]) == len(chart["p90"]) == len(chart["months"])
        assert chart["p10"][-1] <= chart["p50"][-1] <= chart["p90"][-1]
        fd = data["final_distribution"]
        assert 0.0 <= fd["prob_loss_pct"] <= 100.0
        assert fd["p5"] <= fd["median"] <= fd["p95"]
        assert len(data["per_asset"]) == 2
        for a in data["per_asset"]:
            assert a["range_1y_95"][0] < a["range_1y_95"][1]

    def test_projection_empty_portfolio(self):
        token = _register().json()["token"]
        res = client.post("/api/portfolio/projection", json={"years": 5}, headers=_auth_headers(token))
        assert res.status_code == 400

    def test_projection_requires_auth(self):
        res = client.post("/api/portfolio/projection", json={"years": 5})
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Advice
# ---------------------------------------------------------------------------

class TestAdvice:
    def test_advice_empty_portfolio(self):
        token = _register().json()["token"]
        res = client.get("/api/portfolio/advice", headers=_auth_headers(token))
        assert res.status_code == 200
        data = res.json()
        assert data["score"] == 0
        assert data["advice"][0]["type"] == "action"

    def test_advice_with_concentrated_portfolio(self):
        token = _register().json()["token"]
        # One huge position + one small => concentration warning expected
        client.post("/api/portfolio/trade", json={"ticker": "NVDA", "side": "buy", "quantity": 400, "price": 200.0}, headers=_auth_headers(token))
        client.post("/api/portfolio/trade", json={"ticker": "KO", "side": "buy", "quantity": 20, "price": 60.0}, headers=_auth_headers(token))

        with patch.object(portfolio, "get_current_prices", return_value={"NVDA": 200.0, "KO": 60.0}), \
             patch.object(portfolio, "get_tickers_meta", return_value={
                 "NVDA": {"name": "NVIDIA", "sector": "Technology"},
                 "KO": {"name": "Coca-Cola", "sector": "Consumer Defensive"}}), \
             patch.object(portfolio, "fetch_history", side_effect=_fake_history):
            res = client.get("/api/portfolio/advice", headers=_auth_headers(token))

        assert res.status_code == 200
        data = res.json()
        assert 0 <= data["score"] <= 100
        assert len(data["advice"]) > 0
        titles = " ".join(a["title"] for a in data["advice"])
        assert "concentration" in titles.lower() or "NVDA" in titles
        assert any(s["sector"] for s in data["sectors"])

    def test_advice_requires_auth(self):
        res = client.get("/api/portfolio/advice")
        assert res.status_code == 401
