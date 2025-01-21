# FairValue

Calculating intrinsic Value of stocks using SEC fillings.

This repo requires two bulk files:

1. company facts files which contains the public companies SEC fillings. This can be downloaded from here: http://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip.
2. The submissions file is also required as this contains a mapping from the cik filing number used in the SEC filings and the ticker used to identify the stocks listing. This can be found here: https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip.

Once these files have been downloaded and unzipped running:

```bash
make process-data
```


## todo
- 1. handle multiple 10ks in the same year, e.g. multiple filings due to aquisition or merger.
- 2. better handling of tickers with no shares outstanding
- 3. include book value in valuation?
- 4. MSTR: ValidationError: 1 validation error for CompanyFacts
    facts.dei.EntityCommonStockSharesOutstanding
    Field required [type=missing, input_value={'EntityPublicFloat': {'l...frame': 'CY2023Q2I'}]}}}, input_type=dict]
        For further information visit https://errors.pydantic.dev/2.10/v/missing

## Data Quality Issues
- {'cik':889936,'end':'2010-12-31','filed':'2013-02-22'}


## Roadmap
- modelling features:
    - sharpes ratio