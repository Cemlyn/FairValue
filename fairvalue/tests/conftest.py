import os
import pytest

from fairvalue.utils import load_json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def sec_data(company):
    """
    Fixture to load SEC filing data for a given company.

    Args:
        company (str): Company identifier (e.g., 'APPL', 'MSFT'). Defaults to 'APPL'.
    """
    TEST_DATA_PATH = os.path.join(BASE_DIR, "data", company)
    return {
        "company_facts": load_json(
            os.path.join(TEST_DATA_PATH, f"sec-filing-companyfacts-{company}.json")
        ),
        "submissions": load_json(
            os.path.join(TEST_DATA_PATH, f"sec-filing-submissions-{company}.json")
        ),
        "reconciliation-file": load_json(
            os.path.join(TEST_DATA_PATH, f"reconciliation-{company}.json")
        ),
    }
