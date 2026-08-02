import requests
import json
import time

def test_scenario(name, tickers):
    print(f"\n{'='*50}\nTesting Scenario: {name}")
    print(f"Tickers: {tickers}\n{'-'*50}")
    
    url = f"http://localhost:8000/api/analyze"
    query_params = "&".join([f"tickers={t}" for t in tickers])
    full_url = f"{url}?{query_params}"
    
    try:
        response = requests.post(full_url)
        response.raise_for_status()
        data = response.json()
        
        top_10 = data.get("top_10", [])
        print("Top Assets by Sharpe Ratio (Risk vs Expectation):")
        for idx, asset in enumerate(top_10, 1):
            exp_return = asset.get('historical_expected_return', 0) * 100
            risk = asset.get('volatility_risk', 0) * 100
            sharpe = asset.get('sharpe_ratio', 0)
            target = asset.get('analyst_target_price', 'N/A')
            print(f"{idx}. {asset['ticker']} - Exp. Return: {exp_return:.2f}%, Volatility: {risk:.2f}%, Sharpe: {sharpe:.2f}, Target: ${target}")
            
    except Exception as e:
        print(f"Error testing scenario: {e}")

if __name__ == "__main__":
    # Wait a moment for server to boot just in case
    time.sleep(2)
    
    # Scenario 1: Big Tech
    test_scenario("High Growth Tech Stocks", ["AAPL", "MSFT", "NVDA", "TSLA"])
    
    # Scenario 2: Broad Market ETFs vs Safe Havens
    test_scenario("ETFs and Commodities", ["SPY", "QQQ", "GLD", "SLV", "USO"])
    
    # Scenario 3: Defensive vs Cyclical
    test_scenario("Defensive vs Cyclical", ["JNJ", "PFE", "JPM", "XOM", "KO"])
