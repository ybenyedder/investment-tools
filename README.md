# Advanced Investment Analysis Platform

A highly sophisticated, full-stack Investment Analysis Tool designed to help users evaluate financial assets, rank them using quantitative methodologies, perform automated technical analysis, and interact with a fully local LLM assistant to gain deep financial insights.

## 🚀 Key Features

*   **Global Asset Universe:** Instantly analyze massive portfolios, including the live S&P 500 (scraped dynamically), World ETFs, US Tech, and major European and Asian indices.
*   **Fundamental Data Engine:** Fetches live market data and deep fundamental KPIs via `yfinance` including:
    *   PEG Ratio
    *   Return on Equity (ROE)
    *   Debt-to-Equity (DTI)
    *   Profit and Operating Margins
    *   Free Cash Flow vs. Total Debt
*   **Advanced Quantitative Models:**
    *   **Sharpe Ratio, Sortino Ratio, Treynor Ratio:** Dynamically rank assets based on risk-adjusted return profiles.
    *   **Stochastic Modeling:** Project future price boundaries using classical **Black-Scholes** modeling or the **Bachelier** Arithmetic Brownian Motion model.
    *   **Reinforcement Learning (RL):** Automated RL-based backtesting and trading signal generation (BUY/HOLD/SELL) trained on sliced historical windows.
    *   **SARIMA Time-Series:** Forecast 1-year future asset prices using statistical time-series forecasting.
*   **Fully Private Local LLM Assistant:**
    *   Powered by a hyper-efficient `TinyLlama` model running completely locally via `llama-cpp-python`.
    *   Context-aware architecture capable of reading the live analysis data (TAM, Price, RL Actions) to answer your specific financial questions securely—without sending your data to the cloud.
    *   Fully sanitized input pipeline using `bleach` to prevent prompt injection and XSS.
*   **Modern Interactive UI:** Built with **Next.js**, React, and Recharts, featuring a dynamic data table and 10-year historical comparison charts.

## 🛠️ Technology Stack

*   **Backend:** Python 3, FastAPI, Pandas, YFinance, Scikit-Learn, PyPortfolioOpt, Statsmodels, Llama-CPP, Pytest
*   **Frontend:** JavaScript, Next.js, React, Recharts
*   **Security:** Bleach (Input sanitization)

## 📦 Installation & Setup

### 1. Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install fastapi uvicorn yfinance pandas numpy scikit-learn PyPortfolioOpt statsmodels lxml requests bleach pytest llama-cpp-python huggingface_hub
   ```
4. Download the Local LLM:
   Run the setup script to securely download the TinyLlama GGUF model:
   ```bash
   ./install_llm.sh
   ```
5. Run the backend server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### 2. Frontend Setup (Next.js)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node.js dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

## 🧪 Testing

The platform includes a massive non-regression test suite (18+ tests covering deep architectural integrity, edge cases, error handling, quantitative pipelines, and API validation). 

To run the backend tests:
```bash
cd backend
source venv/bin/activate
pytest test_api.py -v
```

## 📜 License

MIT License. Feel free to fork, build, and deploy!
