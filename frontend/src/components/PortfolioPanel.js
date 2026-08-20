'use client';

import { useState, useEffect } from 'react';
import { AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const usd = (v) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(v || 0);
const pct = (v) => `${(v || 0) > 0 ? '+' : ''}${(v || 0).toFixed(2)}%`;

async function fetchPortfolioView(token) {
  const res = await fetch('/api/portfolio', { headers: { 'Authorization': `Bearer ${token}` } });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || 'Erreur de chargement');
  return json;
}

export default function PortfolioPanel({ token, onClose, onCashUpdate, onTrade }) {
  const [view, setView] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('positions');
  const [projection, setProjection] = useState(null);
  const [projLoading, setProjLoading] = useState(false);
  const [advice, setAdvice] = useState(null);
  const [adviceLoading, setAdviceLoading] = useState(false);
  const [history, setHistory] = useState(null);
  const [error, setError] = useState('');

  const authHeaders = { 'Authorization': `Bearer ${token}` };

  // All state updates happen in async callbacks so the effect stays lint-clean.
  const refresh = () => {
    fetchPortfolioView(token)
      .then(json => { setView(json); onCashUpdate?.(json.cash); })
      .catch(e => setError(e.message === 'Failed to fetch' ? 'Connexion au serveur impossible.' : e.message))
      .finally(() => setLoading(false));
  };

  // Initial load
  useEffect(() => {
    fetchPortfolioView(token)
      .then(json => { setView(json); onCashUpdate?.(json.cash); })
      .catch(e => setError(e.message === 'Failed to fetch' ? 'Connexion au serveur impossible.' : e.message))
      .finally(() => setLoading(false));
  }, [token, onCashUpdate]);

  const loadProjection = async () => {
    setProjLoading(true);
    try {
      const res = await fetch('/api/portfolio/projection', {
        method: 'POST', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ years: 5, simulations: 500 })
      });
      const json = await res.json();
      if (!res.ok) { setError(json.detail || 'Projection impossible'); return; }
      setProjection(json);
    } catch {
      setError('Connexion au serveur impossible.');
    } finally {
      setProjLoading(false);
    }
  };

  const loadAdvice = async () => {
    setAdviceLoading(true);
    try {
      const res = await fetch('/api/portfolio/advice', { headers: authHeaders });
      const json = await res.json();
      if (!res.ok) { setError(json.detail || 'Conseils indisponibles'); return; }
      setAdvice(json);
    } catch {
      setError('Connexion au serveur impossible.');
    } finally {
      setAdviceLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      const res = await fetch('/api/portfolio/history', { headers: authHeaders });
      const json = await res.json();
      if (res.ok) setHistory(json);
    } catch { /* silencieux */ }
  };

  const resetPortfolio = async () => {
    if (!window.confirm('Réinitialiser le portefeuille ? Toutes les positions seront supprimées et le cash reviendra à 100 000 $.')) return;
    await fetch('/api/portfolio/reset', { method: 'POST', headers: authHeaders });
    setProjection(null); setAdvice(null);
    refresh();
  };

  const projChartData = projection
    ? projection.chart.months.map((m, i) => ({
        month: `M${Math.round(m)}`,
        band: [projection.chart.p10[i], projection.chart.p90[i]],
        median: projection.chart.p50[i]
      }))
    : [];

  const pnlColor = (v) => (v > 0 ? 'text-emerald-600' : v < 0 ? 'text-red-600' : 'text-slate-600');
  const typeStyles = {
    warning: 'bg-amber-50 border-amber-200 text-amber-900',
    positive: 'bg-emerald-50 border-emerald-200 text-emerald-900',
    action: 'bg-sky-50 border-sky-200 text-sky-900',
    info: 'bg-slate-50 border-slate-200 text-slate-700'
  };
  const typeIcons = { warning: '⚠️', positive: '✅', action: '🎯', info: '💡' };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[55] flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-6xl max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-200 bg-gradient-to-r from-slate-800 to-slate-900 rounded-t-2xl text-white">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-3xl font-bold">Mon Portefeuille</h2>
              {view && (
                <div className="flex flex-wrap gap-x-8 gap-y-1 mt-3">
                  <div><span className="text-slate-400 text-sm">Valeur totale </span><span className="text-2xl font-bold">{usd(view.total_value)}</span></div>
                  <div><span className="text-slate-400 text-sm">Investi </span><span className="font-semibold">{usd(view.invested)}</span></div>
                  <div><span className="text-slate-400 text-sm">Cash </span><span className="font-semibold">{usd(view.cash)}</span></div>
                  <div>
                    <span className="text-slate-400 text-sm">P/L total </span>
                    <span className={`font-bold ${view.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {view.total_pnl >= 0 ? '+' : ''}{usd(view.total_pnl)} ({pct(view.total_return_pct)})
                    </span>
                  </div>
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <button onClick={() => { setLoading(true); refresh(); }} disabled={loading}
                className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-sm cursor-pointer">↻ Actualiser</button>
              <button onClick={resetPortfolio}
                className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-sm cursor-pointer">Réinitialiser</button>
              <button onClick={onClose} className="p-2 text-2xl font-bold text-slate-400 hover:text-white cursor-pointer">&times;</button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 bg-slate-50">
          {[
            ['positions', `Positions${view ? ` (${view.positions.length})` : ''}`],
            ['projection', 'Projection 5 ans'],
            ['advice', 'Conseils'],
            ['history', 'Historique']
          ].map(([key, label]) => (
            <button key={key} onClick={() => {
              setTab(key);
              if (key === 'history' && !history) loadHistory();
            }}
              className={`px-6 py-3 text-sm font-semibold border-b-2 cursor-pointer ${tab === key ? 'border-emerald-600 text-emerald-700 bg-white' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>
              {label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 bg-slate-50">
          {error && <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm">{error}</div>}

          {loading && !view && <div className="text-center text-slate-500 py-12">Chargement du portefeuille…</div>}

          {/* -------- Positions -------- */}
          {view && tab === 'positions' && (
            view.positions.length === 0 ? (
              <div className="text-center py-12 text-slate-500">
                <div className="text-5xl mb-3">📊</div>
                <p className="font-medium">Aucune position pour l&apos;instant.</p>
                <p className="text-sm mt-1">Lancez une analyse puis cliquez sur « Acheter » pour constituer votre portefeuille virtuel.</p>
              </div>
            ) : (
              <div className="overflow-x-auto bg-white rounded-xl border border-slate-200 shadow-sm">
                <table className="w-full border-collapse text-sm whitespace-nowrap text-left">
                  <thead>
                    <tr className="bg-slate-100 text-slate-600 font-semibold uppercase text-xs tracking-wider border-b border-slate-200">
                      <th className="p-3">Action</th>
                      <th className="p-3">Secteur</th>
                      <th className="p-3">Qté</th>
                      <th className="p-3">PRU</th>
                      <th className="p-3">Cours</th>
                      <th className="p-3">Valeur</th>
                      <th className="p-3">P/L</th>
                      <th className="p-3">Poids</th>
                      <th className="p-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {view.positions.map((p) => (
                      <tr key={p.ticker} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="p-3"><strong className="text-slate-900">{p.ticker}</strong><br /><small className="text-slate-500">{p.name}</small></td>
                        <td className="p-3 text-slate-500 text-xs">{p.sector}</td>
                        <td className="p-3">{p.quantity}</td>
                        <td className="p-3">{usd(p.avg_cost)}</td>
                        <td className="p-3">{usd(p.current_price)}</td>
                        <td className="p-3 font-semibold">{usd(p.value)}</td>
                        <td className={`p-3 font-semibold ${pnlColor(p.pnl)}`}>
                          {p.pnl >= 0 ? '+' : ''}{usd(p.pnl)}<br />
                          <small>{pct(p.pnl_pct)}</small>
                        </td>
                        <td className="p-3">
                          <div className="w-20 h-2 bg-slate-200 rounded-full overflow-hidden">
                            <div className="h-full bg-emerald-500" style={{ width: `${Math.min(100, p.weight_pct)}%` }} />
                          </div>
                          <small className="text-slate-500">{p.weight_pct}%</small>
                        </td>
                        <td className="p-3 text-right space-x-1">
                          <button onClick={() => onTrade?.({ ticker: p.ticker, name: p.name, price: p.current_price, side: 'buy' })}
                            className="px-3 py-1.5 rounded-md bg-emerald-100 text-emerald-800 hover:bg-emerald-200 text-xs font-bold cursor-pointer">+ Acheter</button>
                          <button onClick={() => onTrade?.({ ticker: p.ticker, name: p.name, price: p.current_price, side: 'sell' })}
                            className="px-3 py-1.5 rounded-md bg-red-100 text-red-800 hover:bg-red-200 text-xs font-bold cursor-pointer">Vendre</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}

          {/* -------- Projection -------- */}
          {tab === 'projection' && (
            <div>
              {!projection && !projLoading && (
                <div className="text-center py-10">
                  <p className="text-slate-600 mb-4">Simulation Monte Carlo (500 scénarios, rendements et corrélations historiques 3 ans).</p>
                  <button onClick={loadProjection}
                    className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-md cursor-pointer">
                    🔮 Générer la projection à 5 ans
                  </button>
                </div>
              )}
              {projLoading && <div className="text-center text-slate-500 py-12">Simulation en cours…</div>}
              {projection && (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
                    {[
                      ['Rendement annuel attendu', pct(projection.expected_annual_return_pct), 'text-slate-800'],
                      ['Volatilité annuelle', `${projection.annual_volatility_pct.toFixed(1)}%`, 'text-amber-700'],
                      ['Sharpe ratio', projection.sharpe_ratio.toFixed(2), 'text-indigo-700'],
                      ['Médiane à 5 ans', usd(projection.final_distribution.median), 'text-emerald-700'],
                      ['Risque de perte', `${projection.final_distribution.prob_loss_pct}%`, 'text-red-700']
                    ].map(([label, value, color]) => (
                      <div key={label} className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                        <div className="text-xs text-slate-500 uppercase font-bold">{label}</div>
                        <div className={`text-xl font-bold mt-1 ${color}`}>{value}</div>
                      </div>
                    ))}
                  </div>

                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm mb-6">
                    <h3 className="font-bold text-slate-800 mb-4">Évolution projetée de la valeur (bande P10–P90)</h3>
                    <div className="w-full h-[380px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={projChartData}>
                          <defs>
                            <linearGradient id="projBand" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#818cf8" stopOpacity={0.55} />
                              <stop offset="95%" stopColor="#818cf8" stopOpacity={0.08} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                          <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#64748b' }} />
                          <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                          <Tooltip formatter={(val, name) => name === 'Médiane (P50)' ? usd(val) : `P10 : ${usd(val[0])} → P90 : ${usd(val[1])}`}
                            contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                          <Legend />
                          <Area type="monotone" dataKey="band" name="Intervalle P10–P90" stroke="none" fill="url(#projBand)" />
                          <Line type="monotone" dataKey="median" name="Médiane (P50)" stroke="#4f46e5" strokeWidth={2.5} dot={false} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4 text-center text-sm">
                      {[
                        ['P5 (pire)', projection.final_distribution.p5, 'text-red-600'],
                        ['P25', projection.final_distribution.p25, 'text-amber-600'],
                        ['Médiane', projection.final_distribution.median, 'text-emerald-600'],
                        ['P75', projection.final_distribution.p75, 'text-emerald-700'],
                        ['P95 (meilleur)', projection.final_distribution.p95, 'text-indigo-700']
                      ].map(([label, v, color]) => (
                        <div key={label} className="p-2 rounded-lg bg-slate-50 border border-slate-200">
                          <div className="text-xs text-slate-500">{label}</div>
                          <div className={`font-bold ${color}`}>{usd(v)}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                    <h3 className="font-bold text-slate-800 mb-4">Projection par action (1 an, intervalle 95%)</h3>
                    <table className="w-full text-sm text-left">
                      <thead>
                        <tr className="text-slate-500 uppercase text-xs border-b border-slate-200">
                          <th className="py-2">Action</th><th className="py-2">Poids</th><th className="py-2">Rendement attendu</th><th className="py-2">Volatilité</th><th className="py-2">Fourchette 1 an (95%)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {projection.per_asset.map((a) => (
                          <tr key={a.ticker} className="border-b border-slate-100">
                            <td className="py-2 font-semibold text-slate-800">{a.ticker}</td>
                            <td className="py-2">{a.weight_pct}%</td>
                            <td className={`py-2 font-semibold ${pnlColor(a.expected_annual_return_pct)}`}>{pct(a.expected_annual_return_pct)}</td>
                            <td className="py-2">{a.annual_volatility_pct}%</td>
                            <td className="py-2">{usd(a.range_1y_95[0])} → {usd(a.range_1y_95[1])}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}

          {/* -------- Conseils -------- */}
          {tab === 'advice' && (
            <div>
              {!advice && !adviceLoading && (
                <div className="text-center py-10">
                  <p className="text-slate-600 mb-4">Analyse rule-based : concentration, diversification, risque, performance, liquidités.</p>
                  <button onClick={loadAdvice}
                    className="px-6 py-3 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-md cursor-pointer">
                    🧠 Analyser mon portefeuille
                  </button>
                </div>
              )}
              {adviceLoading && <div className="text-center text-slate-500 py-12">Analyse en cours…</div>}
              {advice && (
                <>
                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm mb-6">
                    <div className="flex items-center gap-6">
                      <div className="relative w-28 h-28">
                        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                          <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e2e8f0" strokeWidth="3.8" />
                          <circle cx="18" cy="18" r="15.9" fill="none"
                            stroke={advice.score >= 70 ? '#10b981' : advice.score >= 45 ? '#f59e0b' : '#ef4444'}
                            strokeWidth="3.8" strokeDasharray={`${advice.score} 100`} strokeLinecap="round" />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center text-3xl font-bold text-slate-800">{advice.score}</div>
                      </div>
                      <div>
                        <h3 className="font-bold text-lg text-slate-800">Score de santé du portefeuille</h3>
                        <p className="text-slate-600 text-sm mt-1 max-w-2xl">{advice.summary}</p>
                      </div>
                    </div>
                    {advice.sectors && advice.sectors.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <div className="text-xs font-bold text-slate-500 uppercase">Répartition sectorielle</div>
                        {advice.sectors.map((s) => (
                          <div key={s.sector} className="flex items-center gap-3 text-sm">
                            <div className="w-40 text-slate-600 truncate">{s.sector}</div>
                            <div className="flex-1 h-3 bg-slate-200 rounded-full overflow-hidden">
                              <div className="h-full bg-indigo-500" style={{ width: `${Math.min(100, s.weight_pct)}%` }} />
                            </div>
                            <div className="w-12 text-right text-slate-700 font-medium">{s.weight_pct}%</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {advice.advice.map((a, i) => (
                      <div key={i} className={`p-4 rounded-xl border ${typeStyles[a.type] || typeStyles.info}`}>
                        <div className="font-bold flex items-center gap-2">{typeIcons[a.type] || '💡'} {a.title}</div>
                        <p className="text-sm mt-1 leading-relaxed opacity-90">{a.detail}</p>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* -------- Historique -------- */}
          {tab === 'history' && (
            <div className="overflow-x-auto bg-white rounded-xl border border-slate-200 shadow-sm">
              {!history || history.transactions.length === 0 ? (
                <div className="text-center text-slate-500 py-12">Aucune transaction enregistrée.</div>
              ) : (
                <table className="w-full text-sm text-left">
                  <thead>
                    <tr className="bg-slate-100 text-slate-600 font-semibold uppercase text-xs border-b border-slate-200">
                      <th className="p-3">Date</th><th className="p-3">Sens</th><th className="p-3">Action</th><th className="p-3">Qté</th><th className="p-3">Prix</th><th className="p-3">Frais</th><th className="p-3">Montant</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.transactions.map((t, i) => (
                      <tr key={i} className="border-b border-slate-100">
                        <td className="p-3 text-slate-500">{new Date(t.ts).toLocaleString('fr-FR')}</td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded-md text-xs font-bold ${t.side === 'BUY' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'}`}>
                            {t.side === 'BUY' ? 'ACHAT' : 'VENTE'}
                          </span>
                        </td>
                        <td className="p-3 font-semibold">{t.ticker}</td>
                        <td className="p-3">{t.quantity}</td>
                        <td className="p-3">{usd(t.price)}</td>
                        <td className="p-3">{usd(t.fees)}</td>
                        <td className={`p-3 font-semibold ${t.side === 'BUY' ? 'text-red-600' : 'text-emerald-600'}`}>
                          {t.side === 'BUY' ? '-' : '+'}{usd(t.quantity * t.price)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
