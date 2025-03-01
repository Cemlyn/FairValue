import pytest
from fairvalue.models.ingestion import SECFilings


@pytest.mark.parametrize("company", ["AAPL"])
def test_sec_filing(sec_data):

    sec_filling = SECFilings(
        companyfacts=sec_data["company_facts"], submissions=sec_data["submissions"]
    )

    assert sec_filling.companyfacts.entityName == "Apple Inc."
    assert sec_filling.companyfacts.cik == "320193"

    capexes = sec_filling.companyfacts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units[
        "USD"
    ]
    assert len(capexes) == 90
