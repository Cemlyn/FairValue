import os
import pytest

from fairvalue.utils import load_json
from fairvalue.models.ingestion import SECFilings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def company_facts():
    return load_json(os.path.join(BASE_DIR, "data", "companyfacts-CIK0000320193.json"))


@pytest.fixture
def submissions():
    return load_json(os.path.join(BASE_DIR, "data", "submissions-CIK0000320193.json"))


def test_sec_filing(company_facts, submissions):

    sec_filling = SECFilings(companyfacts=company_facts, submissions=submissions)

    assert sec_filling.companyfacts.entityName == "Apple Inc."
    assert sec_filling.companyfacts.cik == "320193"

    capexes = sec_filling.companyfacts.facts.us_gaap.PaymentsToAcquirePropertyPlantAndEquipment.units[
        "USD"
    ]
    assert len(capexes) == 90
