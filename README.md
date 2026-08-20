# Quantitative Investment Tools Suite

This repository contains a suite of advanced quantitative finance tools designed for stock variation analysis, time-series estimation, and financial data aggregation. 

## 1. Schrödinger Bridge & Fundamentals Estimator

A full-stack web application (FastAPI backend + JavaScript frontend) that utilizes Entropic Optimal Transport to simulate realistic stock price variations and estimate future financial metrics.

### Features
*   **Stochastic Path Simulation:** Generates multiple synthetic price paths connecting an initial price to a target price distribution using the Schrödinger Bridge framework.
*   **Technical Indicator Estimation:** Dynamically computes the Relative Strength Index (RSI - 14 period) and Moving Average Convergence Divergence (MACD) based on the simulated average price path.
*   **Fundamental Estimation:** Calculates mock fundamentals at the target timestamp, estimating the P/E Ratio, Return on Equity (ROE), and EBITDA based on the simulated final price.
*   **Interactive Dashboard:** A frontend UI that allows you to tweak Entropy ($\epsilon$), Volatility, and Target Prices in real-time and visualize the resulting paths and indicators using `Chart.js`.

### How the Estimation is Done (Processing)
1.  **State Space Discretization:** The backend (`app.py`) defines a discretized grid of possible stock prices centered around the initial price.
2.  **Marginal Distributions:** It defines an initial probability distribution (a sharp peak at the current price) and a target probability distribution (a Gaussian curve centered at the expected target price with variance proportional to user-defined volatility).
3.  **Entropic Optimal Transport (Sinkhorn):** The backend runs the **Sinkhorn-Knopp algorithm**. It takes the initial distribution, target distribution, a cost matrix (squared distance between price states), and the user-defined Entropy ($\epsilon$) parameter. It computes the Optimal Transport Plan—a transition probability matrix that minimizes transport cost while maximizing entropy (randomness).
4.  **Brownian Bridge Simulation:** To generate the actual time-series paths, the algorithm samples a final target state using the Sinkhorn transition probabilities. It then connects the initial price to this target state using a randomized Brownian Bridge (adding stochastic noise along the path).
5.  **Metrics Calculation:** The average of these stochastic paths is calculated. Standard formulas (Exponential Moving Averages) are applied to this path to compute MACD and RSI. Stochastic fundamental variables are generated around the mean final price.

### Where the Backend Gets the Information
*   **Data Source:** For this specific estimation tool, the backend relies purely on **mathematical generation based on user inputs** (Initial Price, Target Price, Volatility, Entropy). It does not fetch live market prices for the simulation; it is a generative model used to study theoretical price variations and stress-test scenarios.

---

## 2. Corporate Financial Results Tracker & Database

A robust data pipeline and CLI tool (`finance_tracker.py`) that aggregates the latest corporate earnings reports, maintaining a historical time series and a semantic vector search database.

### Features
*   **Automated Scraping:** Connects to financial news portals to download the latest quarterly results.
*   **Dual-Database Architecture:** 
    *   **SQLite (Time-Series):** Stores structured tabular data (Company Code, Name, Sales, Net Profit, EPS, Result Date). It enforces strict constraints to automatically detect if history is new and ignores duplicate entries.
    *   **ChromaDB (Vector DB):** Converts the financial results into text embeddings. If you query a misspelled company name, it performs a semantic similarity search to find the correct data.
*   **Time-Series Generation:** Extracts a company's historical earnings and formats them into a continuous time series.
*   **Automated Plotting:** If `matplotlib` is installed, it automatically generates a `.png` chart visualizing the historical Net Sales and Net Profit trajectories.

### How the Processing is Done
1.  **Data Extraction:** The script bypasses unreliable HTML table parsing. Instead, it intercepts the hidden Next.js JSON payload (`__NEXT_DATA__`) embedded directly in the page source, ensuring 100% accurate and clean data extraction.
2.  **Validation & Upserting:** The script iterates through the extracted JSON. It attempts to insert each record into SQLite. If the `(company_name, result_date)` combination already exists, it is safely ignored (meaning it natively handles checking for "new history").
3.  **Vectorization:** For new records, the script synthesizes a natural language summary (e.g., *"Company X reported results on Date. Net Sales: Y Cr..."*) and embeds this text into ChromaDB along with queryable metadata.

### Where the Backend Gets the Information
*   **Data Source:** The script fetches live, real-world corporate financial results directly from the **Business Standard Latest Results List** (`https://www.business-standard.com/companies/results/latest-results-list`).
