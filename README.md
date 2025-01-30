# FairValue

Calculating intrinsic Value of stocks using SEC fillings.

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


## todo
- 1. handle multiple 10ks in the same year, e.g. multiple filings due to aquisition or merger.
- 2. better handling of tickers with no shares outstanding
- 3. include book value in valuation?


## Data Quality Issues
- {'cik':889936,'end':'2010-12-31','filed':'2013-02-22'}
- Warner Media group (WM): EntityCommonStockSharesOutstanding states there's only 1069 when there is 142,614,118 class A shares, and 375,380,313 class B.
