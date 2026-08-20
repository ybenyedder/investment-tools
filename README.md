# Quantitative Investment Tools Suite

Suite d'outils de finance quantitative : analyse d'actions, portefeuille virtuel avec achats/ventes au prix réel, projections Monte Carlo et conseils personnalisés.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        docker-compose.yml                        │
├───────────────┬─────────────────┬───────────────────────────────┤
│ web (:8000)   │ backend (:8020) │ frontend (:3000)               │
│ Estimateur    │ API FastAPI     │ Next.js 16 + Recharts          │
│ Schrödinger   │ yfinance, MPT,  │ Dashboard + Portefeuille       │
│ Bridge + UI   │ LLM chat, auth, │ (auth, achat, projection,      │
│ statique      │ portefeuille    │  conseils)                     │
└───────┬───────┴────────┬────────┴───────────────┬───────────────┘
        │                │                       │
        │         ┌──────┴──────┐         ┌──────┴──────┐
        │         │ mongo       │         │ llamacpp    │
        │         │ chromadb    │         │ (TinyLlama) │
        │         │ embeddings  │         └─────────────┘
        │         │ whatsapp-bot│
        │         └─────────────┘
        │
  finance_tracker.py (CLI : scraping Business Standard → SQLite + ChromaDB)
```

## 1. Dashboard d'analyse + Portefeuille virtuel (backend/ + frontend/)

Application full-stack : **API FastAPI** (`backend/main.py`) + **frontend Next.js** (`frontend/`).

### Analyse quantitative
- **Univers d'actifs global** : US, Europe, Asie, ETF, matières premières + S&P 500 complet (Wikipedia)
- **Théorie moderne du portefeuille** : rendements attendus, covariance, Sharpe / Sortino / Treynor
- **Statistiques avancées** : KL divergence, log-vraisemblance, skewness, kurtosis, VaR 95 %, max drawdown
- **Prévisions** : SARIMA 1 an, Black-Scholes (GBM) et Bachelier (ABM) min/max 95 %, cibles analystes
- **Agent RL heuristique** : signal BUY/SELL/HOLD backtesté sur 5 fenêtres glissantes
- **News WhatsApp** : corrélation sémantique via ChromaDB + score d'impact
- **LLM chat** : TinyLlama local (service llamacpp) ou OpenAI distant

### Portefeuille virtuel (paper trading) — NOUVEAU
- **Inscription / connexion** (`backend/portfolio.py`) : mots de passe scrypt, tokens HMAC signés, zéro dépendance externe, SQLite persistant (volume Docker `./backend-data`)
- **Cash virtuel de 100 000 $** par compte
- **Bouton « Acheter »** sur chaque société (tableau Top 10 + fiche détaillée) — exécution au **prix marché réel** (yfinance)
- **Ventes** partielles/totales depuis le panneau portefeuille, P/L latent et réalisé (méthode du coût moyen)
- **Historique** complet des transactions

### Projection & conseils — NOUVEAU
- **Projection Monte Carlo à 5 ans** (500 scénarios) : rendements et corrélations historiques 3 ans, bande P10–P90, distribution finale (P5→P95), probabilité de perte, CAGR médian, Sharpe, projection par action
- **Moteur de conseils** (rule-based) : score de santé /100, alertes de concentration (ligne et secteur), gestion des liquidités, risque (volatilité, Sharpe), performances 1 an, suggestions de rééquilibrage

### Endpoints principaux
| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` / `/api/auth/login` | Inscription / connexion → token |
| GET | `/api/auth/me` | Profil courant |
| GET | `/api/portfolio` | Positions, cash, P/L, poids |
| POST | `/api/portfolio/trade` | Achat/vente au prix marché |
| POST | `/api/portfolio/projection` | Projection Monte Carlo |
| GET | `/api/portfolio/advice` | Conseils + score de santé |
| GET | `/api/portfolio/history` | Historique des transactions |
| POST | `/api/analyze` | Analyse quantitative multi-actifs |
| POST | `/api/chat` | Chat LLM (local/OpenAI) |
| POST | `/api/black-scholes` | Calculateur d'options |
| GET | `/api/search_company` | Recherche mondiale de sociétés |
| GET | `/api/health` | Sonde de vie |

## 2. Estimateur Schrödinger Bridge (app.py + static/) — port 8000

Simulateur de trajectèmes stochastiques (Sinkhorn / pont brownien) avec 3 algorithmes (pure SB, Kalman, hybride), calibration automatique par fenêtre glissante et détection d'anomalies par filtre de Kalman. Sert l'UI sur `/`.

## 3. Tracker de résultats corporate (finance_tracker.py)

Pipeline CLI : scraping Business Standard (payload `__NEXT_DATA__`), stockage SQLite (détection de doublons) + ChromaDB (recherche sémantique), tracés matplotlib.

```bash
python finance_tracker.py --scrape          # récupérer les derniers résultats
python finance_tracker.py --company RELIANCE  # historique d'une société
```

## Déploiement

### Stack complète (Docker Compose)
```bash
docker compose up -d --build
```
| Service | Port hôte | Rôle |
|---|---|---|
| web | 8000 | Estimateur Schrödinger Bridge |
| frontend | 3000 | Dashboard + portefeuille |
| backend | 8020 | API d'analyse (le frontend proxifie `/api` en interne) |
| whatsapp-bot | 8002 | Bot WhatsApp (news) |
| chromadb | 8001 | Vector DB |
| mongo | 27017 | Base documentaire |
| embeddings | 8003 | Service d'embeddings |
| llamacpp | 8080 | TinyLlama (chat local) |

Le portefeuille persiste dans `./backend-data` (monté sur `/app/data`).

### Déploiement distant (deploy.sh)
```bash
# Plus aucun mot de passe dans le fichier : fournissez-le via l'env ou l'invite
DEPLOY_PASSWORD='…' ./deploy.sh
# ou en interactif :
./deploy.sh   # invite de saisie du mot de passe
# ou par clé SSH :
DEPLOY_SSH_KEY=~/.ssh/id_ed25519 ./deploy.sh
```
⚠️ **Sécurité** : un mot de passe SSH a été committé par le passé dans ce dépôt — **changez-le sur le serveur**.

## Développement & tests

```bash
# Backend (depuis backend/)
python -m pytest test_api.py test_portfolio.py -q

# Estimateur (racine)
python -m pytest test_app.py -q

# Frontend (depuis frontend/)
npm run build && npx eslint src/
```

Variables d'environnement utiles : `PORTFOLIO_DB`, `PORTFOLIO_SECRET`, `MONGO_URL`, `CHROMA_URL`, `EMBEDDING_URL`, `LLM_URL`, `ALLOWED_ORIGINS`, `BACKEND_URL` (rewrites Next.js).

> ⚠️ Le portefeuille est un **simulateur** (paper trading) à but pédagogique — aucun ordre réel n'est passé sur un marché.
