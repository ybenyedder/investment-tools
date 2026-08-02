'use client';

import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Bar, Scatter } from 'recharts';

export default function Home() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tickers, setTickers] = useState("AAPL,MSFT,TSLA,SPY,GLD");
  const [quantMethod, setQuantMethod] = useState("sharpe");
  const [stochasticModel, setStochasticModel] = useState("bs");
  const [universe, setUniverse] = useState({});
  const [chatPrompt, setChatPrompt] = useState("");
  const [chatResponse, setChatResponse] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  
  const btnStyle = { padding: '0.4rem 0.8rem', backgroundColor: '#e2e8f0', color: '#1e293b', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9em' };

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/api/universe`)
      .then(res => res.json())
      .then(data => setUniverse(data))
      .catch(console.error);
  }, []);

  const analyze = async () => {
    setLoading(true);
    try {
      const tickerList = tickers.split(',').map(t => t.trim()).filter(Boolean);
      const query = tickerList.map(t => `tickers=${t}`).join('&') + `&quant_method=${quantMethod}`;
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/analyze?${query}`, {
        method: 'POST'
      });
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const askAi = async () => {
    if (!chatPrompt.trim()) return;
    setChatLoading(true);
    setChatResponse("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt: chatPrompt, 
          context: data ? data.top_10 : []
        })
      });
      const json = await res.json();
      setChatResponse(json.response || json.error);
    } catch (err) {
      setChatResponse("Failed to connect to Local LLM.");
    }
    setChatLoading(false);
  };

  const handleCompanySelect = (e) => {
    const selected = e.target.value;
    if (selected) {
      setTickers((prev) => prev ? prev + "," + selected : selected);
      e.target.value = "";
    }
  };

  const handleDomainSelect = (e) => {
    const selected = e.target.value;
    if (selected) {
      setTickers(selected);
      e.target.value = "";
    }
  };

  return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>Investment Analysis Dashboard</h1>
      
      <div style={{ marginBottom: '2rem', padding: '1rem', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
        <h3>Select Tickers and Quantitative Method</h3>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <select 
            onChange={handleDomainSelect}
            style={{ padding: '0.4rem 0.8rem', borderRadius: '4px', border: '1px solid #cbd5e1', color: 'black' }}
            defaultValue=""
          >
            <option value="" disabled>Load Full Domain / Market...</option>
            {universe && Object.keys(universe).map((region) => (
              <optgroup key={`opt-${region}`} label={region}>
                {Object.keys(universe[region]).map((domain) => (
                  <option key={`domain-${domain}`} value={universe[region][domain].join(',')}>
                    {domain}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <select 
            onChange={handleCompanySelect}
            style={{ padding: '0.4rem 0.8rem', borderRadius: '4px', border: '1px solid #cbd5e1', color: 'black' }}
            defaultValue=""
          >
            <option value="" disabled>+ Add Company</option>
            {universe && Object.keys(universe).map((assetClass) => (
              Object.keys(universe[assetClass]).map((category) => (
                <optgroup key={`${assetClass}-${category}`} label={`${assetClass} - ${category}`}>
                  {universe[assetClass][category].map((ticker) => (
                    <option key={ticker} value={ticker}>{ticker}</option>
                  ))}
                </optgroup>
              ))
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', marginBottom: '1rem' }}>
          <input 
            type="text" 
            value={tickers}
            onChange={(e) => setTickers(e.target.value)}
            style={{ flex: 1, padding: '0.5rem', color: 'black' }}
            placeholder="AAPL, MSFT, TSLA..."
          />
          <select 
            value={quantMethod} 
            onChange={(e) => setQuantMethod(e.target.value)}
            style={{ padding: '0.5rem', borderRadius: '4px', color: 'black' }}
          >
            <option value="sharpe">Sharpe Ratio</option>
            <option value="sortino">Sortino Ratio</option>
            <option value="treynor">Treynor Ratio</option>
          </select>
          <select 
            value={stochasticModel} 
            onChange={(e) => setStochasticModel(e.target.value)}
            style={{ padding: '0.5rem', borderRadius: '4px', backgroundColor: '#e0f2fe', color: 'black' }}
          >
            <option value="bs">Black-Scholes (GBM)</option>
            <option value="bachelier">Bachelier Model (ABM)</option>
          </select>
        </div>
        <button 
          onClick={analyze} 
          disabled={loading}
          style={{ padding: '0.5rem 1rem', backgroundColor: '#0070f3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          {loading ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>
      
      {/* Ask Local LLM Section */}
      <div style={{ marginBottom: '2rem', padding: '1rem', backgroundColor: '#eef2ff', borderRadius: '8px', border: '1px solid #c7d2fe' }}>
        <h3 style={{ color: '#3730a3', marginTop: 0 }}>Ask the Local LLM (Investment Assistant)</h3>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <input 
            type="text" 
            value={chatPrompt}
            onChange={(e) => setChatPrompt(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && askAi()}
            style={{ flex: 1, padding: '0.5rem', borderRadius: '4px', border: '1px solid #c7d2fe', color: 'black' }}
            placeholder="e.g. Which of these AI companies has the highest TAM?"
          />
          <button 
            onClick={askAi} 
            disabled={chatLoading}
            style={{ padding: '0.5rem 1rem', backgroundColor: '#4f46e5', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            {chatLoading ? 'Thinking...' : 'Ask AI'}
          </button>
        </div>
        {chatResponse && (
          <div style={{ padding: '1rem', backgroundColor: 'white', borderRadius: '4px', border: '1px solid #e0e7ff', color: '#1e293b' }}>
            <strong style={{ color: '#4f46e5' }}>LLM Response:</strong>
            <p style={{ marginTop: '0.5rem', whiteSpace: 'pre-wrap' }}>{chatResponse}</p>
          </div>
        )}
      </div>

      {data && data.error && (
        <div style={{ color: 'red' }}>Error: {data.error}</div>
      )}

      {data && data.top_10 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
          <div>
            <h2>Top Rankings (Risk vs Expectation)</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#f0f0f0', textAlign: 'left' }}>
                  <th style={{ padding: '0.5rem' }}>Asset</th>
                  <th style={{ padding: '0.5rem' }}>Exp. Return</th>
                  <th style={{ padding: '0.5rem' }}>Risk (Vol)</th>
                  <th style={{ padding: '0.5rem' }}>Sharpe Ratio</th>
                  <th style={{ padding: '0.5rem' }}>Sortino</th>
                  <th style={{ padding: '0.5rem' }}>Treynor</th>
                  <th style={{ padding: '0.5rem' }}>1Y SARIMA</th>
                  <th style={{ padding: '0.5rem' }}>RL Agent Action</th>
                  <th style={{ padding: '0.5rem' }}>RL Acc (Past)</th>
                  <th style={{ padding: '0.5rem' }}>Correlated Asset</th>
                  <th style={{ padding: '0.5rem' }}>SOM/SAM/TAM ($B)</th>
                  <th style={{ padding: '0.5rem' }}>1Y {stochasticModel === 'bs' ? 'BS' : 'Bachelier'} Min/Max</th>
                </tr>
              </thead>
              <tbody>
                {data.top_10.map((item, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #ddd' }}>
                    <td style={{ padding: '0.5rem' }}><strong>{item.ticker}</strong><br/><small>{item.name}</small></td>
                    <td style={{ padding: '0.5rem' }}>{(item.historical_expected_return * 100).toFixed(2)}%</td>
                    <td style={{ padding: '0.5rem' }}>{(item.volatility_risk * 100).toFixed(2)}%</td>
                    <td style={{ padding: '0.5rem', fontWeight: quantMethod === 'sharpe' ? 'bold' : 'normal', backgroundColor: quantMethod === 'sharpe' ? '#e0f2fe' : 'transparent' }}>{item.sharpe_ratio?.toFixed(2)}</td>
                    <td style={{ padding: '0.5rem', fontWeight: quantMethod === 'sortino' ? 'bold' : 'normal', backgroundColor: quantMethod === 'sortino' ? '#e0f2fe' : 'transparent' }}>{item.sortino_ratio?.toFixed(2)}</td>
                    <td style={{ padding: '0.5rem', fontWeight: quantMethod === 'treynor' ? 'bold' : 'normal', backgroundColor: quantMethod === 'treynor' ? '#e0f2fe' : 'transparent' }}>{item.treynor_ratio?.toFixed(2)}</td>
                    <td style={{ padding: '0.5rem', color: '#8884d8', fontWeight: 'bold' }}>{item.sarima_1y_forecast ? `$${item.sarima_1y_forecast.toFixed(2)}` : 'N/A'}</td>
                    <td style={{ padding: '0.5rem' }}>
                      <span style={{ 
                        padding: '4px 8px', borderRadius: '4px', fontSize: '0.85em', fontWeight: 'bold',
                        backgroundColor: item.rl_action?.includes('BUY') ? '#d4edda' : item.rl_action?.includes('SELL') ? '#f8d7da' : '#fff3cd',
                        color: item.rl_action?.includes('BUY') ? '#155724' : item.rl_action?.includes('SELL') ? '#721c24' : '#856404'
                      }}>
                        {item.rl_action} ({item.rl_confidence?.toFixed(0)}%)
                      </span>
                    </td>
                    <td style={{ padding: '0.5rem' }}>{item.rl_backtest_accuracy ? `${item.rl_backtest_accuracy.toFixed(0)}%` : 'N/A'}</td>
                    <td style={{ padding: '0.5rem' }} title={`Corr: ${item.highest_corr_value?.toFixed(2)}`}>{item.highest_corr_ticker}</td>
                    <td style={{ padding: '0.5rem', fontSize: '0.9em' }}>{item.som_b?.toFixed(1)} / {item.sam_b?.toFixed(1)} / {item.tam_b?.toFixed(1)}</td>
                    <td style={{ padding: '0.5rem' }}>
                      {stochasticModel === 'bs' ? (
                        `${item.bs_min_1y_estimation ? `$${item.bs_min_1y_estimation.toFixed(2)}` : 'N/A'} - ${item.bs_max_1y_estimation ? `$${item.bs_max_1y_estimation.toFixed(2)}` : 'N/A'}`
                      ) : (
                        `${item.bachelier_min_1y_estimation ? `$${item.bachelier_min_1y_estimation.toFixed(2)}` : 'N/A'} - ${item.bachelier_max_1y_estimation ? `$${item.bachelier_max_1y_estimation.toFixed(2)}` : 'N/A'}`
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div>
            <h2>Historical Price Trends (10 Years)</h2>
            <div style={{ width: '100%', height: '400px', backgroundColor: '#fafafa', padding: '1rem', borderRadius: '8px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.plot_data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="Date" tick={{fontSize: 12}} tickFormatter={(val) => val.substring(0,4)} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {tickers.split(',').map(t => t.trim()).filter(Boolean).map((ticker, i) => (
                    <Line 
                      key={ticker} 
                      type="monotone" 
                      dataKey={ticker} 
                      stroke={`hsl(${(i * 360) / 10}, 70%, 50%)`} 
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div style={{ marginTop: '2rem' }}>
            <h2>1-Year Price Projections: {stochasticModel === 'bs' ? 'Black-Scholes' : 'Bachelier'} Range & AI Forecasts</h2>
            <div style={{ width: '100%', height: '400px', backgroundColor: '#111827', padding: '1rem', borderRadius: '8px', color: 'white' }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart 
                  layout="vertical" 
                  data={data.top_10.map(t => ({
                    name: t.ticker,
                    current_price: t.current_price,
                    sarima: t.sarima_1y_forecast,
                    range: stochasticModel === 'bs' 
                      ? [t.bs_min_1y_estimation || t.current_price, t.bs_max_1y_estimation || t.current_price]
                      : [t.bachelier_min_1y_estimation || t.current_price, t.bachelier_max_1y_estimation || t.current_price]
                  }))}
                  margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
                >
                  <CartesianGrid stroke="#374151" strokeDasharray="3 3" />
                  <XAxis type="number" stroke="#9ca3af" tickFormatter={(val) => `$${val}`} />
                  <YAxis dataKey="name" type="category" stroke="#9ca3af" width={60} />
                  <Tooltip cursor={{fill: 'rgba(255,255,255,0.1)'}} formatter={(val) => Array.isArray(val) ? `Min: $${val[0].toFixed(2)} - Max: $${val[1].toFixed(2)}` : `$${val.toFixed(2)}`} />
                  <Legend wrapperStyle={{ color: '#fff' }} />
                  <Bar dataKey="range" name={`${stochasticModel === 'bs' ? 'Black-Scholes (GBM)' : 'Bachelier (ABM)'} 95% Expected Range (1Y)`} fill="url(#colorUv)" barSize={20} radius={[10, 10, 10, 10]} />
                  <Scatter dataKey="current_price" name="Current Price" fill="#facc15" shape="star" />
                  <Scatter dataKey="sarima" name="SARIMA 1Y Forecast" fill="#10b981" shape="circle" />
                  <defs>
                    <linearGradient id="colorUv" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="5%" stopColor={stochasticModel === 'bs' ? "#3b82f6" : "#ec4899"} stopOpacity={0.8}/>
                      <stop offset="95%" stopColor={stochasticModel === 'bs' ? "#8b5cf6" : "#f43f5e"} stopOpacity={0.8}/>
                    </linearGradient>
                  </defs>
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
