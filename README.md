# StocksValuation

Calculating intrinsic Value of stocks using SEC fillings.

This repo requires two bulk files:

1. company facts files which contains the public companies SEC fillings. This can be downloaded from here: http://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip.
2. The submissions file is also required as this contains a mapping from the cik filing number used in the SEC filings and the ticker used to identify the stocks listing. This can be found here: https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip.

Once these files have been downloaded and unzipped running:

```bash
make process-data
```
