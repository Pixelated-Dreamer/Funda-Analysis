# Fund Analyzer

A Streamlit app for digging into any public company's fundamentals — no finance degree required.

Enter a ticker symbol, pick a year, and get a scored breakdown of the company's financial health based on equity ratio, profit margin, DCF valuation, and profit growth.

## Features

- **Fundamental Score (0–100)** — weighted across four metrics with a label from Risky to Elite
- **DCF Valuation** — 5-year discounted cash flow model using free cash flow and YoY net income growth
- **Balance Sheet** — assets, liabilities, equity, and equity ratio with benchmarks
- **Income Statement** — full P&L breakdown with net profit margin analysis
- **Stock Chart** — interactive candlestick chart with volume and 20-day MA, selectable time periods
- **Auto-refresh** — data re-fetches from Yahoo Finance every 10 minutes

## Setup

```bash
pip install -r requirements.txt
streamlit run fundaanal.py
```

## Usage

1. Enter a ticker symbol (e.g. `AAPL`, `TSLA`, `MSFT`)
2. Select the fiscal year to analyze
3. Click **Run Analysis**

Data is sourced from Yahoo Finance via `yahooquery`. Some companies may have incomplete data for certain years.

## Scoring Breakdown

| Metric | Max Points |
|---|---|
| Equity Ratio | 25 |
| Net Profit Margin | 25 |
| DCF Valuation vs. Price | 25 |
| YoY Profit Growth | 25 |

| Score | Label |
|---|---|
| 85–100 | Elite |
| 70–84 | Strong |
| 55–69 | Decent |
| 40–54 | Weak |
| 0–39 | Risky |

---

*made with 💜 by Nevaan Kant (xotic)*
