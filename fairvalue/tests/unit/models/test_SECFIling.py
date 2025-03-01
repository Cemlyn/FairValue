import pytest
from fairvalue.models.ingestion import SECFilings


@pytest.mark.parametrize("company", ["AAPL", "NVDA"])
def test_financials_capital_expenditures(sec_data):

    sec_filing = SECFilings(
        companyfacts=sec_data["company_facts"], submissions=sec_data["submissions"]
    )

    capex_values = sec_filing.companyfacts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units[
        "USD"
    ]

    capex_values == sec_data["reconciliation-file"]["capital_expenditures"]


@pytest.mark.parametrize("company", ["AAPL", "NVDA"])
def test_financials_net_ops_cashflows(sec_data):

    sec_filing = SECFilings(
        companyfacts=sec_data["company_facts"], submissions=sec_data["submissions"]
    )

    capex_values = sec_filing.companyfacts.facts.us_gaap.NetCashProvidedByUsedInOperatingActivities.units[
        "USD"
    ]

    capex_values == sec_data["reconciliation-file"]["net_ops_cashflows"]


@pytest.mark.parametrize("company", ["AAPL", "NVDA"])
def test_financials_shares_outstanding(sec_data):

    sec_filing = SECFilings(
        companyfacts=sec_data["company_facts"], submissions=sec_data["submissions"]
    )

    capex_values = (
        sec_filing.companyfacts.facts.us_gaap.CommonStockSharesOutstanding.units[
            "shares"
        ]
    )

    capex_values == sec_data["reconciliation-file"]["shares_outstanding"]
