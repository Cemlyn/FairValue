# FairValue

![Test Status](https://github.com/Cemlyn/FairValue/actions/workflows/test.yml/badge.svg)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Cemlyn_FairValue&metric=coverage)](https://sonarcloud.io/summary/new_code?id=Cemlyn_FairValue)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Cemlyn_FairValue&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=Cemlyn_FairValue)

[![Python Version](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/release/python-312/)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://www.example.com)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A Python library for automated company valuations using Discounted Cash Flow (DCF) analysis, supporting both SEC EDGAR filings and custom financial data.

## Features

- Automated DCF valuation using SEC EDGAR filings
- Support for custom financial data input
- Fast processing of bulk SEC filings. 
- Comprehensive error handling and validation
- Currency-aware calculations (tbd - currently USD only)

## Quick Start

### Using SEC EDGAR Data

```python
from fairvalue import Stock
from fairvalue.models import SECFilings

# Load SEC filing data
secfiling = SECFilings(
    companyfacts='./data/companyfacts/CIK0000320193.json',
    submissions='./data/submissions/CIK0000320193.json'
)

# Create stock and calculate fair value
stock = Stock(sec_filing=secfiling)
valuation = stock.predict_fairvalue(
    growth_rate=0.02,
    number_of_years=10,
    discounting_rate=0.04
)
```

**Output**
```
{
    "ticker_id": "AAPL",
    "exchange": "NONE",
    "cik": "320193",
    "entity_name": "Apple Inc.",
    "days_since_filing": 41,
    "is_potentially_delisted": False,
    "count_filings": 17,
    "forecast_date": "2025-02-20",
    "forecast_horizon": 10,
    "shares_outstanding": 15204137000,
    "company_value": 3886523142972.99,
    "intrinsic_value": 255.62
}
```

### Using Custom Financial Data

```python
from fairvalue import Stock

# Prepare your financial data
financials = {
    'year_end_dates': ['2025-01-01'],
    'free_cashflows': [108807000000],
    'shares_outstanding': [15115823000]
}

# Create stock and calculate fair value
stock = Stock(ticker_id='AAPL', historical_financials=financials)
valuation = stock.predict_fairvalue(
    growth_rate=0.02,
    number_of_years=10,
    discounting_rate=0.04
)
```

**Output:**
```
{
    "ticker_id": "AAPL",
    "exchange": "NONE",
    "cik": None,
    "entity_name": None,
    "count_filings": 1,
    "forecast_date": "2025-02-20",
    "forecast_horizon": 10,
    "shares_outstanding": 15115823000,
    "company_value": 3886523142972.99,
    "intrinsic_value": 257.12
}
```

## Utility Scripts

The `scripts/` directory contains helpful utilities for working with FairValue:

- `download_sec_filings.py`: Download and cache SEC EDGAR filings
- `batch_process.py`: Process multiple companies in batch mode

Run scripts from the project root:
```bash
python scripts/download_sec_filings.py --ticker AAPL
```

## Methodology

### Data Validation
- Robust data validation using Pydantic models
- Automated validation of financial data inputs for both SEC EDGAR and custom financial data

### DCF Calculation
- Based on free cash flow projections
- Uses [Gordon Growth Model](https://www.investopedia.com/ask/answers/032415/what-are-advantages-and-disadvantages-gordon-growth-model.asp) for terminal value. Exit multiple terminal value to be added as an option.
- Does not include debt, assets, or liabilities in calculation. (tbd - will be added in future)

### Key Parameters
- `growth_rate`: Expected annual growth rate of free cash flows
- `number_of_years`: Forecast horizon
- `discounting_rate`: Rate used to discount future cash flows

## Limitations

1. **Company Exclusions**:
   - SPACs and blank check companies
   - Non-US incorporated companies
   - Companies reporting in non-USD currencies

2. **Calculation Scope**:
   - Focuses solely on free cash flows
   - Excludes balance sheet items
   - Does not consider market conditions or company-specific risks

## 🚀 Roadmap & Planned Improvements

### Near Term
- Balance sheet integration for more comprehensive valuations
- Terminal value calculation using exit multiples
- Support for non-US incorporated companies
- data quality indicators

### Medium Term
- Automated growth rate suggestions based on historical data
- Multi-currency support for non-USD financial statements

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## ⚠️ Disclaimer

This software is for educational and research purposes only. It should not be construed as financial advice or a recommendation to buy, sell, or hold any investment or security.

- **No Investment Advice**: The calculations and outputs provided by this tool are based on historical data and assumptions that may not reflect future performance.
- **Not Financial Advice**: Always conduct your own due diligence and consult with qualified financial advisors before making investment decisions.
- **Limited Scope**: The DCF valuation method used here:
  - Does not account for all factors that influence stock prices
  - Uses simplifying assumptions about growth rates and discount rates
  - Does not consider market sentiment, economic conditions, or company-specific risks
- **No Warranty**: This software is provided "as is" without warranty of any kind, either express or implied.

By using this software, you acknowledge and accept these limitations and risks.
