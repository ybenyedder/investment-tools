'use client';

import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function Home() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tickers, setTickers] = useState("AAPL,MSFT,TSLA,SPY,GLD");
  const [universe, setUniverse] = useState({});

  useEffect(() => {
    fetch(process.env.NEXT_PUBLIC_API_URL + '/api/universe' || 'http://localhost:8000/api/universe')
      .then(res => res.json())
      .then(data => setUniverse(data))
      .catch(console.error);
  }, []);

  const analyze = async () => {
    setLoading(true);
    try {
      const tickerList = tickers.split(',').map(t => t.trim()).filter(Boolean);
      const query = tickerList.map(t => `tickers=${t}`).join('&');
      const res = await fetch(`http://localhost:8000/api/analyze?${query}`, {
        method: 'POST'
      });
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>Investment Analysis Dashboard</h1>
      
      <div style={{ marginBottom: '2rem', padding: '1rem', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
        <h3>Select Tickers to Analyze</h3>
        <input 
          type="text" 
          value={tickers}
          onChange={(e) => setTickers(e.target.value)}
          style={{ width: '100%', padding: '0.5rem', marginTop: '0.5rem', marginBottom: '1rem' }}
          placeholder="AAPL, MSFT, TSLA..."
        />
        <button 
          onClick={analyze} 
          disabled={loading}
          style={{ padding: '0.5rem 1rem', backgroundColor: '#0070f3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
        >
          {loading ? 'Analyzing...' : 'Run Analysis'}
        </button>
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
                  <th style={{ padding: '0.5rem' }}>Analyst Target</th>
                </tr>
              </thead>
              <tbody>
                {data.top_10.map((item, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #ddd' }}>
                    <td style={{ padding: '0.5rem' }}><strong>{item.ticker}</strong><br/><small>{item.name}</small></td>
                    <td style={{ padding: '0.5rem' }}>{(item.historical_expected_return * 100).toFixed(2)}%</td>
                    <td style={{ padding: '0.5rem' }}>{(item.volatility_risk * 100).toFixed(2)}%</td>
                    <td style={{ padding: '0.5rem' }}>{item.sharpe_ratio.toFixed(2)}</td>
                    <td style={{ padding: '0.5rem' }}>{item.analyst_target_price ? `$${item.analyst_target_price}` : 'N/A'}</td>
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
        </div>
      )}
    </main>
  );
}
