import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_universe():
    """Test that the universe endpoint returns the correct structure and 200 OK."""
    response = client.get("/api/universe")
    assert response.status_code == 200
    data = response.json()
    assert "US Markets (NASDAQ & NYSE)" in data
    assert "Europe (CAC40, DAX, FTSE, MIB)" in data
    assert "Big Tech / AI" in data["US Markets (NASDAQ & NYSE)"]
    assert "AAPL" in data["US Markets (NASDAQ & NYSE)"]["Big Tech / AI"]
    assert "S&P 500" in data["US Markets (NASDAQ & NYSE)"]
    assert len(data["US Markets (NASDAQ & NYSE)"]["S&P 500"]) > 400

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

def test_analyze_assets_quantitative_method():
    """Test that changing the quant method changes the sorting of the top 10 results."""
    # Test Treynor
    res_treynor = client.post("/api/analyze?tickers=AAPL&tickers=MSFT&tickers=TSLA&quant_method=treynor")
    data_treynor = res_treynor.json()["top_10"]
    assert "treynor_ratio" in data_treynor[0]
    
    # Check it's actually sorted by treynor
    if len(data_treynor) > 1:
        assert data_treynor[0]["treynor_ratio"] >= data_treynor[1]["treynor_ratio"]

def test_analyze_assets_ai_and_advanced_metrics():
    """Test that RL Backtest, TAM/SAM/SOM, Correlation, and SARIMA are returned."""
    response = client.post("/api/analyze?tickers=MSFT")
    assert response.status_code == 200
    data = response.json()
    msft_data = data["analysis"][0]
    
    # AI Models
    assert "sarima_1y_forecast" in msft_data
    assert "rl_action" in msft_data
    assert "rl_backtest_accuracy" in msft_data
    
    # Advanced Metrics
    assert "highest_corr_ticker" in msft_data
    assert "highest_corr_value" in msft_data
    assert "tam_b" in msft_data
    assert "sam_b" in msft_data
    assert "som_b" in msft_data
    
    # Check data sanity
    assert msft_data["rl_backtest_accuracy"] >= 0
    assert msft_data["tam_b"] >= 0

def test_analyze_assets_bachelier():
    """Test that the Bachelier model (Arithmetic Brownian Motion) estimations are returned."""
    response = client.post("/api/analyze?tickers=AAPL")
    assert response.status_code == 200
    data = response.json()
    aapl_data = data["analysis"][0]
    
    assert "bachelier_min_1y_estimation" in aapl_data
    assert "bachelier_max_1y_estimation" in aapl_data
    
    if aapl_data["volatility_risk"] > 0:
        assert aapl_data["bachelier_min_1y_estimation"] < aapl_data["bachelier_max_1y_estimation"]

def test_chat_endpoint():
    """Test the /api/chat endpoint payload serialization and response handling."""
    payload = {
        "prompt": "<script>alert('xss')</script> Which is the best company?",
        "context": [{"ticker": "AAPL", "current_price": 150, "tam_b": 500, "rl_action": "BUY"}]
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # It should either return a valid response or an error (e.g. model downloading).
    # It should not return a 500 error.
    assert "response" in data or "error" in data
    
    # If the response is generated, ensure bleach stripped the script tags
    if "response" in data:
        assert "<script>" not in data["response"]

def test_analyze_assets_fundamentals():
    """Test that fundamental KPIs like PEG, ROE, DTI, Margins, and FCF are present in the response."""
    response = client.post("/api/analyze?tickers=AAPL")
    assert response.status_code == 200
    data = response.json()
    assert len(data["analysis"]) > 0
    
    aapl_data = data["analysis"][0]
    # Check that keys exist (value can be None depending on yfinance data availability, but keys must exist)
    expected_keys = [
        "peg_ratio", "return_on_equity", "debt_to_equity", 
        "profit_margin", "operating_margin", "free_cash_flow", "total_debt"
    ]
    for key in expected_keys:
        assert key in aapl_data

def test_chat_endpoint_empty_prompt():
    """Test that the /api/chat endpoint handles empty prompts securely and doesn't crash."""
    payload = {
        "prompt": "   ",
        "context": [{"ticker": "AAPL", "current_price": 150}]
    }
    response = client.post("/api/chat", json=payload)
    # The server might return a 400 or just a graceful error response, but should not 500
    assert response.status_code in [200, 400]
    data = response.json()
    if response.status_code == 200:
        assert "error" in data or "response" in data

def test_analyze_assets_empty_tickers():
    """Test how the analyze endpoint handles requests with no tickers passed."""
    response = client.post("/api/analyze")
    # It should fall back to the default Query parameter ["AAPL", "MSFT"]
    assert response.status_code == 200
    data = response.json()
    assert len(data["analysis"]) == 2
    tickers = [item["ticker"] for item in data["analysis"]]
    assert "AAPL" in tickers
    assert "MSFT" in tickers

def test_analyze_assets_long_list():
    """Test performance and stability when analyzing a large number of assets simultaneously."""
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "SPY", "GLD"]
    query = "&".join([f"tickers={t}" for t in tickers])
    response = client.post(f"/api/analyze?{query}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["analysis"]) == len(tickers)
    assert len(data["top_10"]) <= 10

def test_chat_endpoint_no_context():
    """Test the /api/chat endpoint when no context list is provided."""
    payload = {
        "prompt": "What is the best investment strategy for a beginner?"
        # Omitting context intentionally
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data or "error" in data

def test_universe_structure_deep():
    """Test deep structural integrity of the newly expanded global asset universe."""
    response = client.get("/api/universe")
    assert response.status_code == 200
    data = response.json()
    assert "Funds & Commodities" in data
    assert "World ETFs" in data["Funds & Commodities"]
    world_etfs = data["Funds & Commodities"]["World ETFs"]
    assert "VT" in world_etfs
    assert "ACWI" in world_etfs
    
    assert "Asia (Nikkei, Chinese, Hang Seng)" in data
    assert "Japan (Nikkei 225)" in data["Asia (Nikkei, Chinese, Hang Seng)"]
    assert "7203.T" in data["Asia (Nikkei, Chinese, Hang Seng)"]["Japan (Nikkei 225)"]

def test_analyze_assets_invalid_quant_method():
    """Test the analyze endpoint with a completely invalid quantitative method."""
    response = client.post("/api/analyze?tickers=AAPL&quant_method=made_up_ratio")
    assert response.status_code == 200
    data = response.json()
    # Should fall back to sharpe_ratio sorting
    assert len(data["analysis"]) == 1

def test_analyze_assets_case_insensitivity():
    """Test that passing lowercase tickers works securely with yfinance."""
    response = client.post("/api/analyze?tickers=aapl&tickers=msft")
    assert response.status_code == 200
    data = response.json()
    assert len(data["analysis"]) == 2
    # yfinance usually standardizes to uppercase, but verify response is successful
    assert data["analysis"][0]["ticker"].upper() in ["AAPL", "MSFT"]

def test_chat_endpoint_missing_prompt():
    """Test the chat endpoint when the prompt field is entirely missing (validation error expected)."""
    payload = {
        "context": [{"ticker": "AAPL", "current_price": 150}]
    }
    response = client.post("/api/chat", json=payload)
    # FastAPI pydantic validation should catch this as a 422 Unprocessable Entity
    assert response.status_code == 422

def test_chat_endpoint_intel_stock_info():
    """Non-regression test to ask LLM for Intel stock information using context."""
    payload = {
        "prompt": "Can you give me all the stock information about Intel?",
        "context": [{
            "ticker": "INTC", 
            "name": "Intel Corporation",
            "current_price": 35.50,
            "sharpe_ratio": 0.4,
            "rl_action": "HOLD",
            "tam_b": 100.5,
            "peg_ratio": 1.2
        }]
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "response" in data or "error" in data
    if "response" in data:
        # Check that the model responded somewhat reasonably and didn't crash
        assert len(data["response"]) > 0

from unittest.mock import patch

@patch("news_correlation.fetch_recent_news")
def test_analyze_assets_news_impact(mock_fetch_news):
    mock_fetch_news.return_value = [{"id":"1","text":"Apple is a great company with high growth.","distance":0.5,"timestamp":"2023"}]
    """Test that the WhatsApp bot news correlation engine successfully appends news_impact_score."""
    response = client.post("/api/analyze?tickers=AAPL")
    assert response.status_code == 200
    data = response.json()
    assert len(data["analysis"]) > 0
    
    aapl_data = data["analysis"][0]
    assert "news_impact_score" in aapl_data
    assert "news_count" in aapl_data
    assert -1.0 <= aapl_data["news_impact_score"] <= 1.0
    assert aapl_data["news_count"] >= 0
