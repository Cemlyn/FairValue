"""
Client for retrieving company filings data from the SEC EDGAR APIs.

The SEC requires every automated request to identify itself with a User-Agent
containing a name and contact email, e.g. "Jane Doe jane@example.com". Pass it
via the `user_agent` argument or set the SEC_USER_AGENT environment variable.

See https://www.sec.gov/os/accessing-edgar-data for the SEC's fair access policy.
"""

import gzip
import json
import os
import threading
import time
from typing import Any, Dict, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fairvalue._exceptions import FairValueException

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

USER_AGENT_ENV_VAR = "SEC_USER_AGENT"

# SEC allows at most 10 requests per second and blocks clients that exceed it.
# Stay well under that limit, shared across every SECClient in the process.
MIN_REQUEST_INTERVAL = 0.2
_throttle_lock = threading.Lock()
_last_request_time = 0.0


def _throttle():
    global _last_request_time  # pylint: disable=global-statement
    with _throttle_lock:
        wait = MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request_time)
        if wait > 0:
            time.sleep(wait)
        _last_request_time = time.monotonic()


def format_cik(cik: str | int) -> str:
    """Zero pad a CIK to the 10 digits used in SEC urls and filenames."""
    return str(int(cik)).zfill(10)


class SECClient:

    def __init__(
        self,
        user_agent: Optional[str] = None,
        cache_dir: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Args:
            user_agent (str, optional): Name and contact email sent to the SEC. Defaults
                to the SEC_USER_AGENT environment variable.
            cache_dir (str, optional): If provided, responses are saved here and re-used
                on later calls, using the same 'companyfacts' and 'submissions' layout
                as the SEC bulk downloads. A relative path is resolved against the
                current working directory when the client is created, and '~' is expanded.
            timeout (float): Request timeout in seconds.
        """
        user_agent = user_agent or os.environ.get(USER_AGENT_ENV_VAR)
        if not user_agent:
            raise FairValueException(
                "The SEC requires a User-Agent identifying you, e.g. 'Jane Doe jane@example.com'. "
                f"Pass 'user_agent' or set the {USER_AGENT_ENV_VAR} environment variable."
            )

        self.user_agent = user_agent
        # resolved once so a later os.chdir doesn't move the cache
        self.cache_dir = (
            os.path.abspath(os.path.expanduser(cache_dir)) if cache_dir else None
        )
        self.timeout = timeout
        self._ticker_map: Optional[Dict[str, str]] = None

    def _get_json(self, url: str) -> Dict[str, Any]:
        _throttle()

        request = Request(
            url,
            headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return json.loads(body)
        except HTTPError as e:
            if e.code == 404:
                raise FairValueException(f"SEC data not found at '{url}'.") from e
            if e.code in (403, 429):
                # deliberately no retry: retrying while blocked extends the block
                raise FairValueException(
                    f"SEC refused the request to '{url}' (HTTP {e.code}). This usually means "
                    "the User-Agent is missing/invalid or the rate limit was exceeded. "
                    "Wait at least 10 minutes before trying again."
                ) from e
            raise FairValueException(
                f"Request to '{url}' failed with HTTP status {e.code}."
            ) from e

    def _get_cached_json(self, url: str, *cache_path: str) -> Dict[str, Any]:
        if self.cache_dir is None:
            return self._get_json(url)

        path = os.path.join(self.cache_dir, *cache_path)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)

        data = self._get_json(url)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file)
        return data

    def lookup_cik(self, ticker: str) -> str:
        """
        Find the CIK for a ticker symbol.

        Args:
            ticker (str): Ticker symbol, e.g. 'AAPL'. Share classes may be written
                either as 'BRK.B' or 'BRK-B'.

        Returns:
            str: 10 digit zero padded CIK.
        """
        if self._ticker_map is None:
            # always fetched fresh as tickers get reassigned between companies
            data = self._get_json(TICKERS_URL)
            self._ticker_map = {
                entry["ticker"].upper(): format_cik(entry["cik_str"])
                for entry in data.values()
            }

        key = ticker.strip().upper().replace(".", "-")
        if key not in self._ticker_map:
            raise FairValueException(f"Ticker '{ticker}' not found in SEC ticker list.")
        return self._ticker_map[key]

    def get_submissions(self, cik: str | int) -> Dict[str, Any]:
        cik = format_cik(cik)
        return self._get_cached_json(
            SUBMISSIONS_URL.format(cik=cik), "submissions", f"CIK{cik}.json"
        )

    def get_companyfacts(self, cik: str | int) -> Dict[str, Any]:
        """
        Fetch the XBRL financial data extracted from all of a company's filings
        (10-K, 10-Q, 20-F etc.).
        """
        cik = format_cik(cik)
        return self._get_cached_json(
            COMPANYFACTS_URL.format(cik=cik), "companyfacts", f"CIK{cik}.json"
        )
