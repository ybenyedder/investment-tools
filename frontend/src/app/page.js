'use client';

import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart, Bar, Scatter } from 'recharts';
import AuthModal from '@/components/AuthModal';
import TradeModal from '@/components/TradeModal';
import PortfolioPanel from '@/components/PortfolioPanel';

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
  const [selectedCompanyInfo, setSelectedCompanyInfo] = useState(null);
  const [llmProvider, setLlmProvider] = useState("local");
  const [llmApiKey, setLlmApiKey] = useState("");

  // Search State
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  // Black-Scholes State
  const [bsParams, setBsParams] = useState({ S: 100, K: 100, T: 1, r: 0.05, sigma: 0.2 });
  const [bsResult, setBsResult] = useState(null);
  const [bsLoading, setBsLoading] = useState(false);

  // Auth & Portfolio State
  const [authToken, setAuthToken] = useState(null);
  const [authUser, setAuthUser] = useState(null);
  const [cash, setCash] = useState(100000);
  const [showAuth, setShowAuth] = useState(false);
  const [showPortfolio, setShowPortfolio] = useState(false);
  const [tradeTarget, setTradeTarget] = useState(null); // {ticker, name, price, side}

  // Restore session from localStorage (validated against the API)
  useEffect(() => {
    const t = typeof window !== 'undefined' ? localStorage.getItem('it_token') : null;
    const email = typeof window !== 'undefined' ? localStorage.getItem('it_user_email') : null;
    if (!t || !email) return;
    fetch('/api/auth/me', { headers: { 'Authorization': `Bearer ${t}` } })
      .then(res => res.ok ? res.json() : Promise.reject())
      .then(me => { setAuthToken(t); setAuthUser(me); })
      .catch(() => {
        localStorage.removeItem('it_token');
        localStorage.removeItem('it_user_email');
      });
  }, []);

  const handleAuthenticated = (token, user) => {
    localStorage.setItem('it_token', token);
    localStorage.setItem('it_user_email', user.email);
    setAuthToken(token);
    setAuthUser(user);
  };

  const logout = () => {
    localStorage.removeItem('it_token');
    localStorage.removeItem('it_user_email');
    setAuthToken(null);
    setAuthUser(null);
    setShowPortfolio(false);
    setCash(100000);
  };

  const openTrade = (target) => {
    if (!authToken) { setShowAuth(true); return; }
    setTradeTarget(target);
  };

  const calculateBS = async () => {
    setBsLoading(true);
    try {
      const apiUrl = "";
      const res = await fetch(`${apiUrl}/api/black-scholes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          S: parseFloat(bsParams.S),
          K: parseFloat(bsParams.K),
          T: parseFloat(bsParams.T),
          r: parseFloat(bsParams.r),
          sigma: parseFloat(bsParams.sigma)
        })
      });
      const json = await res.json();
      setBsResult(json);
    } catch (err) {
      console.error(err);
    }
    setBsLoading(false);
  };

  const handleSearch = async (e) => {
    const q = e.target.value;
    setSearchQuery(q);
    if (q.length > 1) {
      setIsSearching(true);
      try {
        const apiUrl = "";
        const res = await fetch(`${apiUrl}/api/search_company?q=${q}`);
        const data = await res.json();
        setSearchResults(data);
      } catch (err) {
        console.error(err);
      }
      setIsSearching(false);
    } else {
      setSearchResults([]);
    }
  };

  useEffect(() => {
    const apiUrl = "";
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
      const apiUrl = "";
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
      const apiUrl = "";
      const res = await fetch(`${apiUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt: chatPrompt, 
          context: data ? data.top_10 : [],
          provider: llmProvider,
          api_key: llmApiKey
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
    <main className="p-8 font-sans bg-white min-h-screen text-slate-900">
      {/* Header + Auth bar */}
      <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
        <h1 className="text-4xl font-bold">Investment Analysis Dashboard</h1>
        <div className="flex items-center gap-3">
          {authToken ? (
            <>
              <span className="text-sm text-slate-600">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-2 align-middle"></span>
                {authUser?.name || authUser?.email}
                <span className="text-slate-400 ml-2">({new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(cash)} de cash)</span>
              </span>
              <button
                onClick={() => setShowPortfolio(true)}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-md shadow-sm transition-colors cursor-pointer"
              >
                💼 Mon Portefeuille
              </button>
              <button onClick={logout} className="text-sm text-slate-500 hover:text-slate-800 cursor-pointer">Déconnexion</button>
            </>
          ) : (
            <button
              onClick={() => setShowAuth(true)}
              className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-md shadow-sm transition-colors cursor-pointer"
            >
              🔐 Se connecter / S&apos;enregistrer
            </button>
          )}
        </div>
      </div>
      
      <div className="mb-8 p-6 bg-slate-50 rounded-xl shadow-sm border border-slate-200">
        <h3 className="text-xl font-semibold mb-4 text-slate-800">Select Tickers and Quantitative Method</h3>
        <div className="flex gap-2 mb-4 flex-wrap">
          <select 
            onChange={handleDomainSelect}
            className="py-2 px-3 rounded-md border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
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
            className="py-2 px-3 rounded-md border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
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
          <div className="relative">
            <input 
              type="text" 
              placeholder="Search global markets (e.g. Apple)..." 
              value={searchQuery}
              onChange={handleSearch}
              className="py-2 px-3 rounded-md border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm w-72"
            />
            {isSearching && searchQuery.length > 1 && (
              <div className="absolute top-full left-0 mt-1 w-full bg-white border border-slate-200 rounded-md shadow-lg z-50 p-2 text-xs text-slate-500">Searching...</div>
            )}
            {searchResults.length > 0 && (
              <div className="absolute top-full left-0 mt-1 w-full bg-white border border-slate-200 rounded-md shadow-lg z-50 max-h-60 overflow-y-auto">
                {searchResults.map((res, idx) => (
                  <div 
                    key={idx} 
                    className="p-2 hover:bg-blue-50 cursor-pointer border-b border-slate-100 last:border-b-0"
                    onClick={() => {
                      setTickers(prev => prev ? prev + "," + res.ticker : res.ticker);
                      setSearchQuery("");
                      setSearchResults([]);
                    }}
                  >
                    <div className="font-bold text-slate-800 text-sm">{res.ticker}</div>
                    <div className="text-xs text-slate-500 truncate">{res.name}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="flex gap-4 mt-2 mb-6">
          <input 
            type="text" 
            value={tickers}
            onChange={(e) => setTickers(e.target.value)}
            className="flex-1 p-3 rounded-md border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
            placeholder="AAPL, MSFT, TSLA..."
          />
          <select 
            value={quantMethod} 
            onChange={(e) => setQuantMethod(e.target.value)}
            className="p-3 rounded-md border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
          >
            <option value="sharpe">Sharpe Ratio</option>
            <option value="sortino">Sortino Ratio</option>
            <option value="treynor">Treynor Ratio</option>
          </select>
          <select 
            value={stochasticModel} 
            onChange={(e) => setStochasticModel(e.target.value)}
            className="p-3 rounded-md border border-sky-300 bg-sky-50 text-slate-800 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
          >
            <option value="bs">Black-Scholes (GBM)</option>
            <option value="bachelier">Bachelier Model (ABM)</option>
          </select>
        </div>
        <button 
          onClick={analyze} 
          disabled={loading}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 transition-colors text-white font-medium rounded-md cursor-pointer disabled:bg-slate-300 disabled:text-slate-500 disabled:cursor-not-allowed shadow-sm"
        >
          {loading ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>
      
      {/* Ask Local LLM Section */}
      <div className="mb-8 p-6 bg-indigo-50 rounded-xl shadow-sm border border-indigo-200">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-indigo-900 mt-0 mb-0 text-xl font-semibold">Ask the AI Assistant</h3>
          <div className="flex items-center gap-3">
            <select 
              value={llmProvider} 
              onChange={(e) => setLlmProvider(e.target.value)}
              className="py-1 px-2 border border-slate-300 rounded text-sm text-slate-700 bg-white"
            >
              <option value="local">Local LLM (TinyLlama)</option>
              <option value="openai">Remote (OpenAI)</option>
            </select>
            {llmProvider === "openai" && (
              <input 
                type="password" 
                placeholder="sk-..." 
                value={llmApiKey}
                onChange={(e) => setLlmApiKey(e.target.value)}
                className="py-1 px-2 border border-slate-300 rounded text-sm text-slate-700 w-32"
              />
            )}
          </div>
        </div>
        <div className="flex gap-4 mb-4">
          <input 
            type="text" 
            value={chatPrompt}
            onChange={(e) => setChatPrompt(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && askAi()}
            className="flex-1 p-3 rounded-md border border-indigo-200 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
            placeholder="e.g. Which of these AI companies has the highest TAM?"
          />
          <button 
            onClick={askAi} 
            disabled={chatLoading}
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 transition-colors text-white font-medium rounded-md cursor-pointer disabled:bg-indigo-300 disabled:cursor-not-allowed shadow-sm"
          >
            {chatLoading ? 'Thinking...' : 'Ask AI'}
          </button>
        </div>
        {chatResponse && (
          <div className="p-5 bg-white rounded-lg shadow-inner border border-indigo-100 text-slate-800 leading-relaxed">
            <strong className="text-indigo-700 uppercase tracking-wide text-xs">LLM Response:</strong>
            <p className="mt-2 whitespace-pre-wrap">{chatResponse}</p>
          </div>
        )}
      </div>

      {/* Black-Scholes Calculator */}
      <div className="mb-8 p-6 bg-teal-50 rounded-xl shadow-sm border border-teal-200">
        <h3 className="text-teal-900 mt-0 mb-4 text-xl font-semibold">Options Pricing (Black-Scholes)</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
          <div>
            <label className="block text-xs font-bold text-teal-800 uppercase">Stock Price ($)</label>
            <input type="number" step="0.01" value={bsParams.S} onChange={e => setBsParams({...bsParams, S: e.target.value})} className="w-full p-2 mt-1 rounded border border-teal-200" />
          </div>
          <div>
            <label className="block text-xs font-bold text-teal-800 uppercase">Strike Price ($)</label>
            <input type="number" step="0.01" value={bsParams.K} onChange={e => setBsParams({...bsParams, K: e.target.value})} className="w-full p-2 mt-1 rounded border border-teal-200" />
          </div>
          <div>
            <label className="block text-xs font-bold text-teal-800 uppercase">Time (Years)</label>
            <input type="number" step="0.1" value={bsParams.T} onChange={e => setBsParams({...bsParams, T: e.target.value})} className="w-full p-2 mt-1 rounded border border-teal-200" />
          </div>
          <div>
            <label className="block text-xs font-bold text-teal-800 uppercase">Risk-Free Rate</label>
            <input type="number" step="0.01" value={bsParams.r} onChange={e => setBsParams({...bsParams, r: e.target.value})} className="w-full p-2 mt-1 rounded border border-teal-200" />
          </div>
          <div>
            <label className="block text-xs font-bold text-teal-800 uppercase">Volatility (σ)</label>
            <input type="number" step="0.01" value={bsParams.sigma} onChange={e => setBsParams({...bsParams, sigma: e.target.value})} className="w-full p-2 mt-1 rounded border border-teal-200" />
          </div>
        </div>
        <button 
          onClick={calculateBS} 
          disabled={bsLoading}
          className="px-6 py-2 bg-teal-600 hover:bg-teal-700 transition-colors text-white font-medium rounded-md cursor-pointer disabled:bg-teal-300 shadow-sm"
        >
          {bsLoading ? 'Calculating...' : 'Calculate Options Price'}
        </button>

        {bsResult && (
          <div className="mt-4 p-4 bg-white rounded-lg shadow-inner border border-teal-100 flex gap-8">
            <div>
              <div className="text-xs text-teal-600 uppercase font-bold tracking-wide">Call Option Value</div>
              <div className="text-2xl font-bold text-teal-900">${bsResult.call_price?.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs text-teal-600 uppercase font-bold tracking-wide">Put Option Value</div>
              <div className="text-2xl font-bold text-teal-900">${bsResult.put_price?.toFixed(2)}</div>
            </div>
          </div>
        )}
      </div>

      {data && data.error && (
        <div className="text-red-700 bg-red-50 p-4 rounded-md border border-red-200 font-semibold mb-6 shadow-sm">
          Error: {data.error}
        </div>
      )}

      {data && data.top_10 && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          <div className="overflow-x-auto bg-white p-6 rounded-xl border border-slate-200 shadow-sm col-span-1 xl:col-span-2">
            <h2 className="text-2xl mb-6 font-bold text-slate-800 border-b border-slate-200 pb-2">Top Rankings (Risk vs Expectation)</h2>
            <table className="w-full border-collapse text-sm whitespace-nowrap text-left">
              <thead>
                <tr className="bg-slate-50 text-slate-600 font-semibold uppercase text-xs tracking-wider border-b border-slate-200">
                  <th className="p-3 rounded-tl-md">Asset</th>
                  <th className="p-3 bg-indigo-50 text-indigo-900 border-l border-r border-indigo-100">WhatsApp News Impact</th>
                  <th className="p-3">Exp. Return</th>
                  <th className="p-3">Risk (Vol)</th>
                  <th className="p-3">Sharpe Ratio</th>
                  <th className="p-3">Sortino</th>
                  <th className="p-3">Treynor</th>
                  <th className="p-3">1Y SARIMA</th>
                  <th className="p-3">RL Agent Action</th>
                  <th className="p-3">RL Acc (Past)</th>
                  <th className="p-3">Correlated Asset</th>
                  <th className="p-3">SOM/SAM/TAM ($B)</th>
                  <th className="p-3">PEG</th>
                  <th className="p-3">ROE</th>
                  <th className="p-3">DTI (Debt/Eq)</th>
                  <th className="p-3">Margins (Prof/Op)</th>
                  <th className="p-3">FCF/Debt ($B)</th>
                  <th className="p-3 rounded-tr-md">1Y {stochasticModel === 'bs' ? 'BS' : 'Bachelier'} Min/Max</th>
                </tr>
              </thead>
              <tbody className="text-slate-600">
                {data.top_10.map((item, i) => (
                  <tr key={i} onClick={() => setSelectedCompanyInfo(item)} className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer">
                    <td className="p-3">
                      <strong className="text-slate-900 text-base">{item.ticker}</strong><br/>
                      <small className="text-slate-500">{item.name}</small>
                      <div className="mt-1.5">
                        <button
                          onClick={(e) => { e.stopPropagation(); openTrade({ ticker: item.ticker, name: item.name, price: item.current_price, side: 'buy' }); }}
                          className="px-3 py-1 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition-colors cursor-pointer"
                        >
                          Acheter
                        </button>
                      </div>
                    </td>
                    <td className="p-3 bg-indigo-50/30 border-l border-r border-indigo-50">
                      <div className="flex flex-col items-center">
                        <span className={`px-2 py-1 rounded-md font-bold text-xs ${item.news_impact_score > 0.2 ? 'bg-green-100 text-green-700' : item.news_impact_score < -0.2 ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
                          {item.news_impact_score > 0 ? '+' : ''}{(item.news_impact_score * 100).toFixed(1)}%
                        </span>
                        <span className="text-[10px] text-indigo-400 mt-1">{item.news_count} news</span>
                      </div>
                    </td>
                    <td className="p-3 font-medium text-slate-800">{(item.historical_expected_return * 100).toFixed(2)}%</td>
                    <td className="p-3 font-medium text-slate-800">{(item.volatility_risk * 100).toFixed(2)}%</td>
                    <td className={`p-3 ${quantMethod === 'sharpe' ? 'font-bold bg-sky-50 text-sky-900 rounded-l-sm' : ''}`}>{item.sharpe_ratio?.toFixed(2)}</td>
                    <td className={`p-3 ${quantMethod === 'sortino' ? 'font-bold bg-sky-50 text-sky-900 rounded-l-sm' : ''}`}>{item.sortino_ratio?.toFixed(2)}</td>
                    <td className={`p-3 ${quantMethod === 'treynor' ? 'font-bold bg-sky-50 text-sky-900 rounded-l-sm' : ''}`}>{item.treynor_ratio?.toFixed(2)}</td>
                    <td className="p-3 text-indigo-600 font-bold bg-indigo-50/30">{item.sarima_1y_forecast ? `$${item.sarima_1y_forecast.toFixed(2)}` : 'N/A'}</td>
                    <td className="p-3">
                      <span className={`px-2 py-1.5 rounded-md text-xs font-bold tracking-wide ${item.rl_action?.includes('BUY') ? 'bg-green-100 text-green-800' : item.rl_action?.includes('SELL') ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}`}>
                        {item.rl_action} ({item.rl_confidence?.toFixed(0)}%)
                      </span>
                    </td>
                    <td className="p-3 font-medium">{item.rl_backtest_accuracy ? `${item.rl_backtest_accuracy.toFixed(0)}%` : 'N/A'}</td>
                    <td className="p-3 text-slate-500" title={`Corr: ${item.highest_corr_value?.toFixed(2)}`}>{item.highest_corr_ticker}</td>
                    <td className="p-3 text-xs text-slate-500">{item.som_b?.toFixed(1)} / {item.sam_b?.toFixed(1)} / {item.tam_b?.toFixed(1)}</td>
                    <td className="p-3 text-slate-700">{item.peg_ratio ? item.peg_ratio.toFixed(2) : 'N/A'}</td>
                    <td className="p-3">{item.return_on_equity ? (item.return_on_equity * 100).toFixed(1) + '%' : 'N/A'}</td>
                    <td className="p-3">{item.debt_to_equity ? item.debt_to_equity.toFixed(1) + '%' : 'N/A'}</td>
                    <td className="p-3 text-xs text-slate-500">
                      {item.profit_margin ? (item.profit_margin * 100).toFixed(1) + '%' : 'N/A'} / {item.operating_margin ? (item.operating_margin * 100).toFixed(1) + '%' : 'N/A'}
                    </td>
                    <td className="p-3 text-xs text-slate-500">
                      {item.free_cash_flow ? (item.free_cash_flow / 1e9).toFixed(1) : 'N/A'} / {item.total_debt ? (item.total_debt / 1e9).toFixed(1) : 'N/A'}
                    </td>
                    <td className="p-3 text-sm text-slate-700 font-medium">
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

          <div className="col-span-1 xl:col-span-1">
            <h2 className="text-2xl mb-4 font-bold text-slate-800 border-b border-slate-200 pb-2">Historical Price Trends (10 Years)</h2>
            <div className="w-full h-[450px] bg-slate-50 p-6 rounded-xl shadow-inner border border-slate-200">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.plot_data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="Date" tick={{fontSize: 12, fill: '#64748b'}} tickFormatter={(val) => val.substring(0,4)} axisLine={{stroke: '#cbd5e1'}} />
                  <YAxis tick={{fontSize: 12, fill: '#64748b'}} axisLine={{stroke: '#cbd5e1'}} tickFormatter={(val) => `$${val}`} />
                  <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  {tickers.split(',').map(t => t.trim()).filter(Boolean).map((ticker, i) => (
                    <Line 
                      key={ticker} 
                      type="monotone" 
                      dataKey={ticker} 
                      stroke={`hsl(${(i * 360) / Math.max(1, tickers.split(',').filter(Boolean).length)}, 75%, 55%)`} 
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 6 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div className="col-span-1 xl:col-span-1">
            <h2 className="text-2xl mb-4 font-bold text-slate-800 border-b border-slate-200 pb-2">1-Year Price Projections</h2>
            <div className="w-full h-[450px] bg-slate-900 p-6 rounded-xl shadow-lg border border-slate-800 text-white">
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
                  margin={{ top: 10, right: 20, bottom: 10, left: 20 }}
                >
                  <CartesianGrid stroke="#334155" strokeDasharray="4 4" />
                  <XAxis type="number" stroke="#94a3b8" tickFormatter={(val) => `$${val}`} axisLine={{stroke: '#475569'}} />
                  <YAxis dataKey="name" type="category" stroke="#f8fafc" width={60} axisLine={{stroke: '#475569'}} tick={{fontWeight: '500'}} />
                  <Tooltip cursor={{fill: 'rgba(255,255,255,0.05)'}} formatter={(val) => Array.isArray(val) ? `Min: $${val[0].toFixed(2)} - Max: $${val[1].toFixed(2)}` : `$${val.toFixed(2)}`} contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f8fafc' }} />
                  <Legend wrapperStyle={{ color: '#cbd5e1', paddingTop: '15px' }} />
                  <Bar dataKey="range" name={`${stochasticModel === 'bs' ? 'Black-Scholes (GBM)' : 'Bachelier (ABM)'} 95% Expected Range (1Y)`} fill="url(#colorUv)" barSize={24} radius={[6, 6, 6, 6]} />
                  <Scatter dataKey="current_price" name="Current Price" fill="#fbbf24" shape="star" />
                  <Scatter dataKey="sarima" name="SARIMA 1Y Forecast" fill="#34d399" shape="circle" />
                  <defs>
                    <linearGradient id="colorUv" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="5%" stopColor={stochasticModel === 'bs' ? "#3b82f6" : "#ec4899"} stopOpacity={0.9}/>
                      <stop offset="95%" stopColor={stochasticModel === 'bs' ? "#8b5cf6" : "#f43f5e"} stopOpacity={0.9}/>
                    </linearGradient>
                  </defs>
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
          {selectedCompanyInfo && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
            <div className="p-6 border-b border-slate-200 flex justify-between items-center bg-slate-50 rounded-t-2xl">
              <div>
                <h2 className="text-3xl font-bold text-slate-800">{selectedCompanyInfo.name} <span className="text-slate-500 text-xl font-normal ml-2">({selectedCompanyInfo.ticker})</span></h2>
                <div className="flex gap-3 mt-2 text-sm text-slate-600">
                  <span>{selectedCompanyInfo.sector}</span>
                  <span>&bull;</span>
                  <span>{selectedCompanyInfo.country}</span>
                  <span>&bull;</span>
                  <span className="font-semibold text-slate-900">Current Price: ${selectedCompanyInfo.current_price?.toFixed(2)}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => openTrade({ ticker: selectedCompanyInfo.ticker, name: selectedCompanyInfo.name, price: selectedCompanyInfo.current_price, side: 'buy' })}
                  className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg shadow-sm transition-colors cursor-pointer"
                >
                  💰 Acheter cette action
                </button>
                <button onClick={() => setSelectedCompanyInfo(null)} className="text-slate-400 hover:text-slate-700 p-2 text-2xl font-bold">&times;</button>
              </div>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1 bg-white">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                
                {/* Left Column: Quantitative & Fundamentals */}
                <div className="space-y-6">
                  <div className="bg-slate-50 rounded-xl p-5 border border-slate-200">
                    <h3 className="text-lg font-bold text-slate-800 mb-4 border-b border-slate-200 pb-2">Quantitative & Risk</h3>
                    <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-sm">
                      <div className="text-slate-500">Expected Return</div>
                      <div className="font-semibold text-slate-900 text-right">{(selectedCompanyInfo.historical_expected_return * 100).toFixed(2)}%</div>
                      <div className="text-slate-500">Volatility (Risk)</div>
                      <div className="font-semibold text-slate-900 text-right">{(selectedCompanyInfo.volatility_risk * 100).toFixed(2)}%</div>
                      <div className="text-slate-500" title="Kullback-Leibler Divergence (vs Normal Dist)">KL Divergence (vs Normal)</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.kl_divergence != null ? selectedCompanyInfo.kl_divergence.toFixed(4) : 'N/A'}</div>
                      <div className="text-slate-500">Log-Likelihood</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.log_likelihood != null ? selectedCompanyInfo.log_likelihood.toFixed(2) : 'N/A'}</div>
                      <div className="text-slate-500">Skewness / Kurtosis</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.skewness != null ? selectedCompanyInfo.skewness.toFixed(2) : 'N/A'} / {selectedCompanyInfo.kurtosis != null ? selectedCompanyInfo.kurtosis.toFixed(2) : 'N/A'}</div>
                      <div className="text-slate-500">Value at Risk (95%)</div>
                      <div className="font-semibold text-slate-900 text-right text-red-600">{selectedCompanyInfo.var_95 != null ? (selectedCompanyInfo.var_95 * 100).toFixed(2) + '%' : 'N/A'}</div>
                      <div className="text-slate-500">Max Drawdown</div>
                      <div className="font-semibold text-slate-900 text-right text-red-600">{selectedCompanyInfo.max_drawdown != null ? (selectedCompanyInfo.max_drawdown * 100).toFixed(2) + '%' : 'N/A'}</div>
                      <div className="text-slate-500">Sharpe Ratio</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.sharpe_ratio?.toFixed(2)}</div>
                      <div className="text-slate-500">Sortino Ratio</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.sortino_ratio?.toFixed(2)}</div>
                      <div className="text-slate-500">Treynor Ratio</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.treynor_ratio?.toFixed(2)}</div>
                    </div>
                  </div>

                  <div className="bg-slate-50 rounded-xl p-5 border border-slate-200">
                    <h3 className="text-lg font-bold text-slate-800 mb-4 border-b border-slate-200 pb-2">AI Forecast & Estimates</h3>
                    <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-sm">
                      <div className="text-slate-500">SARIMA 1Y Forecast</div>
                      <div className="font-bold text-indigo-700 text-right">${selectedCompanyInfo.sarima_1y_forecast?.toFixed(2)}</div>
                      <div className="text-slate-500">RL Agent Action</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.rl_action} ({selectedCompanyInfo.rl_confidence?.toFixed(0)}%)</div>
                      <div className="text-slate-500">BS (GBM) 1Y Max</div>
                      <div className="font-semibold text-slate-900 text-right">${selectedCompanyInfo.bs_max_1y_estimation?.toFixed(2)}</div>
                      <div className="text-slate-500">Bachelier 1Y Max</div>
                      <div className="font-semibold text-slate-900 text-right">${selectedCompanyInfo.bachelier_max_1y_estimation?.toFixed(2)}</div>
                      <div className="text-slate-500">Analyst Target</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.analyst_target_price ? '$'+selectedCompanyInfo.analyst_target_price.toFixed(2) : 'N/A'}</div>
                    </div>
                  </div>
                </div>

                {/* Right Column: WhatsApp News & Correlation */}
                <div className="space-y-6">
                  <div className="bg-indigo-50/50 rounded-xl p-5 border border-indigo-100">
                    <div className="flex justify-between items-center mb-4 border-b border-indigo-100 pb-2">
                      <h3 className="text-lg font-bold text-indigo-900">WhatsApp Real-Time News</h3>
                      <span className={"px-3 py-1 rounded-full text-xs font-bold " + (selectedCompanyInfo.news_impact_score > 0.2 ? "bg-green-100 text-green-800" : selectedCompanyInfo.news_impact_score < -0.2 ? "bg-red-100 text-red-800" : "bg-slate-200 text-slate-700")}>
                        Impact Score: {selectedCompanyInfo.news_impact_score > 0 ? '+' : ''}{(selectedCompanyInfo.news_impact_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    
                    <div className="space-y-4">
                      {selectedCompanyInfo.news_list && selectedCompanyInfo.news_list.length > 0 ? (
                        selectedCompanyInfo.news_list.map((news, idx) => (
                          <div key={idx} className="bg-white p-4 rounded-lg shadow-sm border border-slate-100 text-sm text-slate-700 leading-relaxed">
                            {news}
                          </div>
                        ))
                      ) : (
                        <div className="bg-white p-4 rounded-lg shadow-sm border border-slate-100 text-sm text-slate-500 italic text-center">
                          {selectedCompanyInfo.latest_news || "No recent news found in WhatsApp DB."}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="bg-slate-50 rounded-xl p-5 border border-slate-200">
                    <h3 className="text-lg font-bold text-slate-800 mb-4 border-b border-slate-200 pb-2">Fundamentals ($B)</h3>
                    <div className="grid grid-cols-2 gap-y-3 gap-x-4 text-sm">
                      <div className="text-slate-500">SOM / SAM / TAM</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.som_b?.toFixed(1)} / {selectedCompanyInfo.sam_b?.toFixed(1)} / {selectedCompanyInfo.tam_b?.toFixed(1)}</div>
                      <div className="text-slate-500">Free Cash Flow</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.free_cash_flow ? (selectedCompanyInfo.free_cash_flow/1e9).toFixed(1) : 'N/A'}</div>
                      <div className="text-slate-500">Total Debt</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.total_debt ? (selectedCompanyInfo.total_debt/1e9).toFixed(1) : 'N/A'}</div>
                      <div className="text-slate-500">Profit Margin</div>
                      <div className="font-semibold text-slate-900 text-right">{selectedCompanyInfo.profit_margin ? (selectedCompanyInfo.profit_margin*100).toFixed(1)+'%' : 'N/A'}</div>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Financial Trajectories Graph */}
              {selectedCompanyInfo.revenue_trajectory && Object.keys(selectedCompanyInfo.revenue_trajectory).length > 0 && (
                <div className="mt-8 bg-slate-50 rounded-xl p-5 border border-slate-200">
                  <h3 className="text-lg font-bold text-slate-800 mb-4 border-b border-slate-200 pb-2">Financial Trajectories ($ Billions)</h3>
                  <div className="w-full h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart 
                        data={Object.keys(selectedCompanyInfo.revenue_trajectory).sort().map(year => ({
                          year,
                          Revenue: (selectedCompanyInfo.revenue_trajectory[year] || 0) / 1e9,
                          NetIncome: (selectedCompanyInfo.net_income_trajectory?.[year] || 0) / 1e9,
                          OPEX: (selectedCompanyInfo.opex_trajectory?.[year] || 0) / 1e9,
                          CAPEX: Math.abs(selectedCompanyInfo.capex_trajectory?.[year] || 0) / 1e9,
                          NFP: (selectedCompanyInfo.net_financial_position_trajectory?.[year] || 0) / 1e9
                        }))}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="year" tick={{fontSize: 12, fill: '#64748b'}} />
                        <YAxis tick={{fontSize: 12, fill: '#64748b'}} tickFormatter={(val) => `$${val}B`} />
                        <Tooltip formatter={(val) => `$${val.toFixed(2)}B`} contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                        <Legend />
                        <Line type="monotone" dataKey="Revenue" stroke="#3b82f6" strokeWidth={2} activeDot={{ r: 6 }} />
                        <Line type="monotone" dataKey="NetIncome" stroke="#10b981" strokeWidth={2} />
                        <Line type="monotone" dataKey="OPEX" stroke="#f59e0b" strokeWidth={2} />
                        <Line type="monotone" dataKey="CAPEX" stroke="#ef4444" strokeWidth={2} />
                        <Line type="monotone" dataKey="NFP" stroke="#8b5cf6" strokeWidth={2} name="Net Fin Position" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4 text-xs text-slate-500 text-center">
                    <div>Rev Volatility: <span className="font-bold text-slate-700">{(selectedCompanyInfo.revenue_volatility * 100).toFixed(1)}%</span></div>
                    <div>Net Inc Volatility: <span className="font-bold text-slate-700">{(selectedCompanyInfo.net_income_volatility * 100).toFixed(1)}%</span></div>
                    <div>OPEX Volatility: <span className="font-bold text-slate-700">{(selectedCompanyInfo.opex_volatility * 100).toFixed(1)}%</span></div>
                    <div>CAPEX Volatility: <span className="font-bold text-slate-700">{(selectedCompanyInfo.capex_volatility * 100).toFixed(1)}%</span></div>
                    <div>NFP Volatility: <span className="font-bold text-slate-700">{(selectedCompanyInfo.net_financial_position_volatility * 100).toFixed(1)}%</span></div>
                  </div>
                </div>
              )}
            </div>
            
            <div className="p-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl text-right">
              <button onClick={() => setSelectedCompanyInfo(null)} className="px-6 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 font-medium transition-colors cursor-pointer">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Auth modal */}
      {showAuth && (
        <AuthModal
          onClose={() => setShowAuth(false)}
          onAuthenticated={handleAuthenticated}
        />
      )}

      {/* Portfolio panel */}
      {showPortfolio && authToken && (
        <PortfolioPanel
          token={authToken}
          onClose={() => setShowPortfolio(false)}
          onCashUpdate={setCash}
          onTrade={(target) => setTradeTarget(target)}
        />
      )}

      {/* Buy/Sell trade modal */}
      {tradeTarget && authToken && (
        <TradeModal
          ticker={tradeTarget.ticker}
          name={tradeTarget.name}
          currentPrice={tradeTarget.price}
          side={tradeTarget.side || 'buy'}
          cash={cash}
          token={authToken}
          onClose={() => setTradeTarget(null)}
          onDone={() => {/* le panneau se réactualise de lui-même */}}
        />
      )}

    </main>
  );
}
