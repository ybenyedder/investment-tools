import requests
import time

def test_scenario(name, tickers):
    print(f"\n{'='*60}\nEvaluating Scenario: {name}")
    print(f"Tickers: {', '.join(tickers)}\n{'-'*60}")
    
    url = f"http://localhost:8000/api/analyze"
    query_params = "&".join([f"tickers={t}" for t in tickers])
    full_url = f"{url}?{query_params}"
    
    try:
        response = requests.post(full_url)
        response.raise_for_status()
        data = response.json()
        
        top_10 = data.get("top_10", [])
        print(f"{'Rank':<5} | {'Ticker':<6} | {'Exp. Return':<12} | {'Risk (Vol)':<12} | {'Sharpe':<8} | {'Analyst Target':<15}")
        print("-" * 75)
        for idx, asset in enumerate(top_10, 1):
            exp_return = asset.get('historical_expected_return', 0) * 100
            risk = asset.get('volatility_risk', 0) * 100
            sharpe = asset.get('sharpe_ratio', 0)
            target = asset.get('analyst_target_price')
            target_str = f"${target:.2f}" if target else "N/A"
            
            print(f"{idx:<5} | {asset['ticker']:<6} | {exp_return:>8.2f}%   | {risk:>8.2f}%   | {sharpe:>6.2f}   | {target_str:<15}")
            
    except Exception as e:
        print(f"Error testing scenario: {e}")

if __name__ == "__main__":
    print("Initializing test script against live API (fetching 10-year data & analyst estimates)...")
    time.sleep(1) # Ensure backend is ready
    
    # 1. Semiconductors (Requested: NXP, TI)
    test_scenario(
        "Semiconductors (NXP, Texas Instruments, etc.)", 
        ["NXPI", "TXN", "TSM", "AMD", "INTC"]
    )
    
    # 2. Artificial Intelligence (AI)
    test_scenario(
        "Artificial Intelligence Leaders", 
        ["NVDA", "MSFT", "PLTR", "GOOGL", "META"]
    )
    
    # 3. Power Storage & Clean Energy
    test_scenario(
        "Power Storage & Clean Energy", 
        ["FLNC", "ENPH", "SEDG", "TSLA", "ALB"]
    )
    
    # 4. World's Best Places to Invest (Geographic ETFs)
    test_scenario(
        "Global Geographic ETFs (US, Europe, Emerging, India, China)", 
        ["SPY", "VGK", "VWO", "INDA", "MCHI"]
    )
