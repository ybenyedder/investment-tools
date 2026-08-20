let priceChart = null;
let techChart = null;

async function runSimulation() {
    const payload = {
        initial_price: parseFloat(document.getElementById('init_price').value),
        target_price: parseFloat(document.getElementById('target_price').value),
        volatility: parseFloat(document.getElementById('volatility').value),
        epsilon: parseFloat(document.getElementById('epsilon').value),
        steps: 100,
        num_paths: 10
    };

    const response = await fetch('/api/estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await response.json();
    
    updateMetrics(data.metrics);
    drawCharts(data.paths, data.indicators);
}

async function autoCalibrate() {
    // Generate a mock historical price series (100 days) with some variation/regime change
    let prices = [120.0];
    let volatility = 0.15;
    for (let i = 1; i < 100; i++) {
        // Introduce a regime change at day 50
        if (i === 50) volatility = 0.35; 
        let drift = 0.05 / 252;
        let shock = (Math.random() - 0.5) * 2 * (volatility / Math.sqrt(252));
        prices.push(prices[i-1] * Math.exp(drift + shock));
    }

    const payload = {
        prices: prices,
        window: 20, // 20-day sliding window
        steps_ahead: 100
    };

    const response = await fetch('/api/calibrate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await response.json();

    if (data.error) {
        alert(data.error);
        return;
    }

    // Update the UI parameters with the calibrated values
    document.getElementById('init_price').value = data.current_price;
    document.getElementById('target_price').value = data.calibrated_target_price;
    document.getElementById('volatility').value = data.calibrated_volatility;
    document.getElementById('epsilon').value = data.calibrated_epsilon;

    alert(`Calibration complete!\nDetected Volatility: ${data.calibrated_volatility}\nEstimated Epsilon: ${data.calibrated_epsilon}`);
}

function updateMetrics(metrics) {
    document.getElementById('val_price').innerText = `$${metrics.mean_final_price}`;
    document.getElementById('val_per').innerText = `${metrics.estimated_per}x`;
    document.getElementById('val_roe').innerText = `${metrics.estimated_roe}%`;
    document.getElementById('val_ebitda').innerText = `$${metrics.estimated_ebitda.toLocaleString()}`;
    document.getElementById('val_rsi').innerText = metrics.latest_rsi;
    document.getElementById('val_macd').innerText = metrics.latest_macd;
}

function drawCharts(paths, indicators) {
    const labels = Array.from({length: paths[0].length}, (_, i) => i);
    
    // Price Chart
    const priceCtx = document.getElementById('priceChart').getContext('2d');
    if(priceChart) priceChart.destroy();
    
    const datasets = paths.map((path, i) => ({
        label: `Path ${i+1}`,
        data: path,
        borderColor: `hsla(${Math.random() * 360}, 70%, 50%, 0.5)`,
        borderWidth: 1,
        fill: false,
        pointRadius: 0
    }));

    priceChart = new Chart(priceCtx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { title: { display: true, text: 'Price' } } }
        }
    });
    
    // Tech Chart
    const techCtx = document.getElementById('techChart').getContext('2d');
    if(techChart) techChart.destroy();
    
    techChart = new Chart(techCtx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'RSI (14)',
                    data: indicators.rsi,
                    borderColor: 'blue',
                    borderWidth: 2,
                    yAxisID: 'y',
                    pointRadius: 0
                },
                {
                    label: 'MACD',
                    data: indicators.macd,
                    borderColor: 'red',
                    borderWidth: 2,
                    yAxisID: 'y1',
                    pointRadius: 0
                },
                {
                    label: 'Signal',
                    data: indicators.macd_signal,
                    borderColor: 'orange',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    yAxisID: 'y1',
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: { type: 'linear', display: true, position: 'left', min: 0, max: 100, title: { display: true, text: 'RSI' } },
                y1: { type: 'linear', display: true, position: 'right', title: { display: true, text: 'MACD' }, grid: { drawOnChartArea: false } }
            }
        }
    });
}

// Run once on load
window.onload = runSimulation;
