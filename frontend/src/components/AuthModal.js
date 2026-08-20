'use client';

import { useState } from 'react';

export default function AuthModal({ onClose, onAuthenticated }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const body = mode === 'login'
        ? { email, password }
        : { email, password, name };
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const json = await res.json();
      if (!res.ok) {
        setError(json.detail || (typeof json.detail === 'object' ? 'Formulaire invalide' : 'Erreur'));
        return;
      }
      onAuthenticated(json.token, json.user);
      onClose();
    } catch (err) {
      setError('Connexion au serveur impossible.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
        <div className="px-6 pt-6 pb-4 border-b border-slate-200 bg-gradient-to-r from-emerald-600 to-teal-600">
          <h2 className="text-2xl font-bold text-white">
            {mode === 'login' ? 'Connexion' : 'Créer un compte'}
          </h2>
          <p className="text-emerald-100 text-sm mt-1">
            Sauvegardez votre portefeuille d&apos;actions virtuel — 100 000 $ de cash de départ.
          </p>
        </div>

        <form onSubmit={submit} className="p-6 space-y-4">
          {mode === 'register' && (
            <div>
              <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Nom (optionnel)</label>
              <input
                type="text" value={name} onChange={(e) => setName(e.target.value)}
                className="w-full p-3 rounded-md border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="Votre nom"
                maxLength={80}
              />
            </div>
          )}
          <div>
            <label className="block text-xs font-bold text-slate-600 uppercase mb-1">Email</label>
            <input
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full p-3 rounded-md border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="vous@exemple.com"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-600 uppercase mb-1">
              Mot de passe {mode === 'register' && <span className="normal-case font-normal">(8 caractères min.)</span>}
            </label>
            <input
              type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full p-3 rounded-md border border-slate-300 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="••••••••"
              minLength={mode === 'register' ? 8 : 1}
            />
          </div>

          {error && (
            <div className="p-3 rounded-md bg-red-50 border border-red-200 text-red-700 text-sm">
              {Array.isArray(error) ? 'Vérifiez les champs du formulaire.' : error}
            </div>
          )}

          <button
            type="submit" disabled={loading}
            className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-md transition-colors disabled:bg-emerald-300 cursor-pointer"
          >
            {loading ? 'Patientez…' : (mode === 'login' ? 'Se connecter' : 'Créer mon compte')}
          </button>

          <button
            type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}
            className="w-full text-sm text-emerald-700 hover:text-emerald-900 cursor-pointer"
          >
            {mode === 'login' ? "Pas encore de compte ? S'enregistrer" : 'Déjà un compte ? Se connecter'}
          </button>
        </form>

        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 text-right">
          <button onClick={onClose} className="text-slate-500 hover:text-slate-800 text-sm cursor-pointer">Fermer</button>
        </div>
      </div>
    </div>
  );
}
