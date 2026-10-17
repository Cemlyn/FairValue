import gzip
import io
import json
import os
from urllib.error import HTTPError

import pytest

from fairvalue import Stock
from fairvalue._exceptions import FairValueException
from fairvalue.models.sec_ingestion import SECFilings
from fairvalue import sec_client
from fairvalue.sec_client import SECClient, format_cik

USER_AGENT = "Test User test@example.com"

TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 1067983, "ticker": "BRK-B", "title": "BERKSHIRE HATHAWAY INC"},
}


class FakeResponse(io.BytesIO):
    def __init__(self, body: bytes, gzipped: bool = False):
        super().__init__(gzip.compress(body) if gzipped else body)
        self.headers = {"Content-Encoding": "gzip"} if gzipped else {}


@pytest.fixture
def fake_sec(monkeypatch):
    """Replaces urlopen with a fake serving canned responses. Records requests made."""
    responses = {}
    requests = []

    def fake_urlopen(request, timeout=None):
        requests.append(request)
        if request.full_url not in responses:
            raise HTTPError(request.full_url, 404, "Not Found", {}, None)
        response = responses[request.full_url]
        if isinstance(response, Exception):
            raise response
        return FakeResponse(json.dumps(response).encode("utf-8"), gzipped=True)

    monkeypatch.setattr(sec_client, "urlopen", fake_urlopen)
    monkeypatch.setattr(sec_client, "MIN_REQUEST_INTERVAL", 0.0)
    responses[sec_client.TICKERS_URL] = TICKERS
    return responses, requests


def test_format_cik():
    assert format_cik(320193) == "0000320193"
    assert format_cik("0000320193") == "0000320193"


def test_requires_user_agent(monkeypatch):
    monkeypatch.delenv(sec_client.USER_AGENT_ENV_VAR, raising=False)
    with pytest.raises(FairValueException, match="User-Agent"):
        SECClient()


def test_user_agent_from_env(monkeypatch):
    monkeypatch.setenv(sec_client.USER_AGENT_ENV_VAR, USER_AGENT)
    assert SECClient().user_agent == USER_AGENT


def test_sends_user_agent(fake_sec):
    _, requests = fake_sec
    SECClient(user_agent=USER_AGENT).lookup_cik("AAPL")
    assert requests[0].get_header("User-agent") == USER_AGENT


@pytest.mark.parametrize(
    "ticker,expected",
    [("AAPL", "0000320193"), ("aapl", "0000320193"), ("BRK.B", "0001067983")],
)
def test_lookup_cik(fake_sec, ticker, expected):
    assert SECClient(user_agent=USER_AGENT).lookup_cik(ticker) == expected


def test_lookup_cik_fetches_ticker_list_once(fake_sec):
    _, requests = fake_sec
    client = SECClient(user_agent=USER_AGENT)
    client.lookup_cik("AAPL")
    client.lookup_cik("BRK-B")
    assert len(requests) == 1


def test_lookup_cik_unknown_ticker(fake_sec):
    with pytest.raises(FairValueException, match="not found"):
        SECClient(user_agent=USER_AGENT).lookup_cik("NOTATICKER")


@pytest.mark.parametrize("status", [403, 429])
def test_blocked_request_is_not_retried(fake_sec, status):
    responses, requests = fake_sec
    url = sec_client.SUBMISSIONS_URL.format(cik="0000320193")
    responses[url] = HTTPError(url, status, "Blocked", {}, None)

    with pytest.raises(FairValueException, match="10 minutes"):
        SECClient(user_agent=USER_AGENT).get_submissions(320193)
    assert len(requests) == 1


def test_cache_dir_reuses_responses(fake_sec, tmp_path):
    responses, requests = fake_sec
    url = sec_client.COMPANYFACTS_URL.format(cik="0000320193")
    responses[url] = {"cik": 320193}

    client = SECClient(user_agent=USER_AGENT, cache_dir=str(tmp_path))
    assert client.get_companyfacts(320193) == {"cik": 320193}
    assert client.get_companyfacts(320193) == {"cik": 320193}

    assert len(requests) == 1
    assert os.path.exists(tmp_path / "companyfacts" / "CIK0000320193.json")


@pytest.mark.parametrize("company", ["AAPL"])
def test_secfilings_from_ticker(fake_sec, sec_data):
    responses, _ = fake_sec
    responses[sec_client.COMPANYFACTS_URL.format(cik="0000320193")] = sec_data[
        "company_facts"
    ]
    responses[sec_client.SUBMISSIONS_URL.format(cik="0000320193")] = sec_data[
        "submissions"
    ]

    sec_filing = SECFilings.from_ticker("AAPL", user_agent=USER_AGENT)
    expected = SECFilings(
        companyfacts=sec_data["company_facts"], submissions=sec_data["submissions"]
    )

    assert sec_filing.companyfacts.entityName == "Apple Inc."
    assert sec_filing.to_annual_financials() == expected.to_annual_financials()

    valuation = Stock(sec_filing=sec_filing).predict_fairvalue(
        growth_rate=0.02, number_of_years=10, discounting_rate=0.04
    )
    assert valuation["ticker_id"] == "AAPL"
    assert valuation["intrinsic_value"] > 0
