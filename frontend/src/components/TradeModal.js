'use client';

import { useState } from 'react';

const usd = (v) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(v || 0);

export default function TradeModal({ ticker, name, currentPrice, side, cash, token, onClose, onDone }) {
  const [quantity, setQuantity] = useState(1);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);

  const qty = parseFloat(quantity) || 0;
  const total = qty * (currentPrice || 0);
  const isBuy = side === 'buy';

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (qty <= 0) { setError('Quantité invalide.'); return; }
    setLoading(true);
    try {
      const res = await fetch('/api/portfolio/trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ ticker, side, quantity: qty })
      });
      const json = await res.json();
      if (!res.ok) { setError(json.detail || 'Ordre refusé.'); return; }
      setSuccess(json);
      onDone(json);
    } catch (err) {
      setError('Connexion au serveur impossible.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[70] flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
        <div className={`px-6 py-5 border-b ${isBuy ? 'bg-gradient-to-r from-emerald-600 to-green-600' : 'bg-gradient-to-r from-rose-600 to-red-600'}`}>
          <h2 className="text-2xl font-bold text-white">
            {isBuy ? 'Acheter' : 'Vendre'} {ticker}
          </h2>
          <p className="text-white/80 text-sm mt-1">{name} — cours actuel : {usd(currentPrice)}</p>
        </div>

        {success ? (
          <div className="p-6">
            <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800">
              <div className="font-bold text-lg mb-2">✅ Ordre exécuté</div>
              <div className="text-sm space-y-1">
                <div>{success.side === 'BUY' ? 'Achat' : 'Vente'} de {success.quantity} {ticker} à {usd(success.price)}</div>
                <div>Cash restant : <strong>{usd(success.cash_after)}</strong></div>
              </div>
            </div>
            <button onClick={onClose} className="mt-4 w-full py-3 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-md cursor-pointer">
              Fermer
            </button>
          </div>
        ) : (
          <form onSubmit={submit} className="p-6 space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Quantité d&apos;actions</label>
              <input
                type="number" min="0.000001" step="any" value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full p-3 rounded-md border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-lg"
              />
              <div className="flex gap-2 mt-2">
                {[1, 5, 10, 25, 50].map((q) => (
                  <button key={q} type="button" onClick={() => setQuantity(q)}
                    className="px-3 py-1 text-xs rounded-full border border-slate-300 hover:bg-slate-100 cursor-pointer">{q}</button>
                ))}
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-1 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Montant de l&apos;ordre</span><span className="font-bold text-slate-900">{usd(total)}</span></div>
              {isBuy && <div className="flex justify-between"><span className="text-slate-500">Cash disponible</span><span className="font-semibold text-slate-700">{usd(cash)}</span></div>}
              {isBuy && total > cash && <div className="text-red-600 font-semibold">⚠ Cash insuffisant pour cet ordre</div>}
            </div>

            {error && <div className="p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm">{error}</div>}

            <button
              type="submit" disabled={loading || (isBuy && total > cash)}
              className={`w-full py-3 text-white font-semibold rounded-md transition-colors cursor-pointer disabled:opacity-50 ${isBuy ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'}`}
            >
              {loading ? 'Exécution…' : `${isBuy ? 'Confirmer l\'achat' : 'Confirmer la vente'} — ${usd(total)}`}
            </button>
          </form>
        )}

        {!success && (
          <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 text-right">
            <button onClick={onClose} className="text-slate-500 hover:text-slate-800 text-sm cursor-pointer">Annuler</button>
          </div>
        )}
      </div>
    </div>
  );
}
