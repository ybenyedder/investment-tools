import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_universe():
    """Test that the universe endpoint returns the correct structure and 200 OK."""
    response = client.get("/api/universe")
    assert response.status_code == 200
    data = response.json()
    assert "Stocks" in data
    assert "ETFs" in data
    assert "Commodities" in data
    assert "Technology" in data["Stocks"]
    assert "AAPL" in data["Stocks"]["Technology"]

def test_analyze_assets_success():
    """Test the core analyze endpoint with valid standard tickers."""
    response = client.post("/api/analyze?tickers=AAPL&tickers=MSFT")
    assert response.status_code == 200
    data = response.json()
    
    # Assert JSON structure
    assert "analysis" in data
    assert "top_10" in data
    assert "plot_data" in data
    
    # Check that AAPL and MSFT are in the results
    tickers = [item["ticker"] for item in data["analysis"]]
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    
    # Ensure calculations were performed
    aapl_data = next(item for item in data["analysis"] if item["ticker"] == "AAPL")
    assert "historical_expected_return" in aapl_data
    assert "sharpe_ratio" in aapl_data
    assert aapl_data["sharpe_ratio"] >= -10  # basic bounds check
    
def test_analyze_assets_nan_regression():
    """
    Non-regression test to ensure assets with missing historical data (e.g., FLNC, PLTR)
    do not cause a 500 JSON serialization error due to NaN values.
    """
    response = client.post("/api/analyze?tickers=FLNC&tickers=PLTR")
    assert response.status_code == 200  # Should not be 500
    data = response.json()
    assert "analysis" in data
    assert len(data["analysis"]) > 0
    
def test_analyze_assets_invalid_ticker():
    """Test handling of invalid or non-existent tickers."""
    response = client.post("/api/analyze?tickers=INVALIDTICKER123")
    assert response.status_code == 200
    data = response.json()
    # Depending on yfinance behavior, it may return empty dataframe
    assert "error" in data or len(data.get("analysis", [])) == 0

def test_analyze_assets_black_scholes():
    """Test that the Black-Scholes Geometric Brownian Motion estimations are returned."""
    response = client.post("/api/analyze?tickers=AAPL")
    assert response.status_code == 200
    data = response.json()
    
    assert "analysis" in data
    assert len(data["analysis"]) > 0
    
    aapl_data = data["analysis"][0]
    
    # Assert that the min/max fields exist
    assert "bs_min_1y_estimation" in aapl_data
    assert "bs_max_1y_estimation" in aapl_data
    
    bs_min = aapl_data["bs_min_1y_estimation"]
    bs_max = aapl_data["bs_max_1y_estimation"]
    
    # Check that they are valid numbers and min < max if volatility is > 0
    if aapl_data["volatility_risk"] > 0:
        assert bs_min is not None
        assert bs_max is not None
        assert bs_min < bs_max
