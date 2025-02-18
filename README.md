# FairValue

FairValue is a python tool used to:
1. programatically calculate intrinsic value estimates for companies based on annualised cashflow projections
2. Use SEC bulk data on company filiings to make informed valuations

## Generating Intrinsic Value

**Input**
```Python
from fairvalue import Stock

financials = {'year_end_dates':['2025-01-01'],
              'free_cashflows':[108807000000],
              'shares_outstanding':[15115823000]}

stock = Stock(ticker_id='AAPL',
      historical_financials=financials)

stock.predict_fairvalue(growth_rate=0.02,
                        number_of_years=10,
                        discounting_rate=0.04)
```

**Output:**
```json
{
    "ticker_id": "AAPL",
    "exchange": "NONE",
    "cik": null,
    "entity_name": null,
    "last_filing_date": "2025-01-01",
    "days_since_filiing": 46,
    "number_of_historical_filings": 1,
    "forecast_date": "2025-02-16",
    "forecast_horizon": 10,
    "shares_outstanding": 15115823000,
    "latest_company_value": 3886523142972.99,
    "latest_intrinsic_value": 257.12
}
```

## Using SEC Filing
The SEC offers filings in the form json file. FairValue can process the filing into a tabular form and generate a valuation.

**Input**
```python
from fairvalue import Stock
from fairvalue.models import SECFilings

secfiling = SECFilings(companyfacts='./data/companyfacts/CIK0000320193.json',
                         submissions='./data/submissions/CIK0000320193.json')

stock = Stock(sec_filing=secfiling)

stock.predict_fairvalue(growth_rate=0.02,
                        number_of_years=10,
                        discounting_rate=0.04)
```

**Output**
```json
{
    "ticker_id": "AAPL",
    "exchange": "Nasdaq",
    "cik": "320193",
    "entity_name": "Apple Inc.",
    "last_filing_date": "2024-09-28",
    "days_since_filiing": 141,
    "number_of_historical_filings": 17,
    "forecast_date": "2025-02-16",
    "forecast_horizon": 10,
    "shares_outstanding": 15204137000,
    "latest_company_value": 3886523142972.99,
    "latest_intrinsic_value": 255.62
}
```


This repo requires two bulk files:

1. company facts files which contains the public companies SEC fillings. This can be downloaded from here: http://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip.
2. The submissions file is also required as this contains a mapping from the cik filing number used in the SEC filings and the ticker used to identify the stocks listing. This can be found here: https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip.

Once these files have been downloaded and unzipped running:

```bash
make process-data
```

```python
make process-data
```

## Gaps
1. Does not process companies which fall into the categories below. During ingestion these companies will fail validation:
    - blank check companies or SPACs
    - Companies incorporated in outside the USA
    - Companies who have non-USD currencies listed on the net ops cashfow or capital expenditures.

2. Intrinsic Valuecalculation does not factor in debt and book value, being purely based on free cashflow.


## Data Quality Issues
- {'cik':889936,'end':'2010-12-31','filed':'2013-02-22'}
- Warner Media group (WM): EntityCommonStockSharesOutstanding states there's only 1069 when there is 142,614,118 class A shares, and 375,380,313 class B.
