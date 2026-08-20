from fastapi.testclient import TestClient
from app import app
import numpy as np

client = TestClient(app)

def test_estimate_endpoint_basic():
    payload = {
        "initial_price": 100.0,
        "target_price": 110.0,
        "volatility": 0.2,
        "epsilon": 1.0,
        "steps": 10,
        "num_paths": 2
    }
    response = client.post("/api/estimate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "paths" in data
    assert "metrics" in data
    assert "indicators" in data
    
    assert len(data["paths"]) == 2
    assert len(data["paths"][0]) == 10
    
    metrics = data["metrics"]
    assert "mean_final_price" in metrics
    assert "estimated_per" in metrics
    assert "estimated_roe" in metrics
    assert "estimated_ebitda" in metrics

def test_estimate_endpoint_kalman_and_hybrid():
    for algo in ["kalman", "hybrid"]:
        payload = {
            "initial_price": 100.0,
            "target_price": 110.0,
            "volatility": 0.2,
            "epsilon": 1.0,
            "steps": 10,
            "num_paths": 2,
            "algorithm": algo
        }
        response = client.post("/api/estimate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert len(data["paths"]) == 2

def test_calibrate_endpoint_success():
    # Simulate a price series
    prices = [100.0 + i for i in range(30)]
    payload = {
        "prices": prices,
        "window": 10,
        "steps_ahead": 50
    }
    response = client.post("/api/calibrate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "calibrated_volatility" in data
    assert "calibrated_target_price" in data
    assert "calibrated_epsilon" in data
    assert "current_price" in data
    
    assert data["current_price"] == 129.0 # the last element

def test_calibrate_endpoint_insufficient_data():
    # Too few prices -> rejected by validation (422)
    payload = {
        "prices": [100.0, 101.0],
        "window": 10
    }
    response = client.post("/api/calibrate", json=payload)
    assert response.status_code == 422

    # Valid list length but window larger than data -> graceful error, no 500
    payload = {
        "prices": [100.0, 101.0, 102.0, 103.0],
        "window": 10
    }
    response = client.post("/api/calibrate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "error" in data

def test_estimate_endpoint_validation():
    """Invalid parameters must be rejected with 422, never crash the server."""
    bad_payloads = [
        {"steps": 0},                          # division by zero guard
        {"steps": -5},
        {"num_paths": 0},
        {"initial_price": -10.0},              # log() guard
        {"target_price": 0.0},
        {"volatility": 0.0},
        {"epsilon": -1.0},
        {"algorithm": "nonexistent_algo"},
    ]
    for extra in bad_payloads:
        payload = {
            "initial_price": 100.0,
            "target_price": 110.0,
            "volatility": 0.2,
            "epsilon": 1.0,
            "steps": 10,
            "num_paths": 2,
        }
        payload.update(extra)
        response = client.post("/api/estimate", json=payload)
        assert response.status_code == 422, f"expected 422 for {extra}, got {response.status_code}"

    # Non-positive prices in calibrate must be rejected (log-space)
    response = client.post("/api/calibrate", json={"prices": [100.0, -5.0, 102.0], "window": 2})
    assert response.status_code == 422

def test_root_serves_ui():
    """The estimator UI must be served at / (was a 404)."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_calibrate_endpoint_anomaly():
    # Simulate a steady price series, then a massive spike to trigger the Kalman Filter anomaly
    prices = [100.0] * 25
    prices.extend([150.0, 200.0, 300.0, 500.0]) # Huge sudden spike
    
    payload = {
        "prices": prices,
        "window": 10,
        "steps_ahead": 50
    }
    response = client.post("/api/calibrate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "kf_target_price" in data
    assert "anomaly_detected" in data
    assert "anomaly_msg" in data
    
    # Because of the massive spike, the sliding window drift will be huge compared to the KF state
    assert data["anomaly_detected"] is True
    assert "ANOMALY DETECTED" in data["anomaly_msg"]
