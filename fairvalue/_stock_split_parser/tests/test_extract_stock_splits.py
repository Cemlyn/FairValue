import json
import pytest

from ..extract_stock_splits import normalize_ratio, normalize_date


@pytest.mark.parametrize(
    "input_ratio,expected",
    [
        ("2-for-1", "2:1"),
        ("2 for 1", "2:1"),
        ("2-to-1", "2:1"),
        ("2 to 1", "2:1"),
        ("2to1", "2:1"),
        ("2for1", "2:1"),
        ("2\tfor\t1", "2:1"),
        ("2  for 1", "2:1"),
        ("3-for-2", "3:2"),
        ("4-for-1", "4:1"),
        ("10-for-1", "10:1"),
        ("2:1", "2:1"),
        ("3 : 2", "3:2"),
        ("not specified", None),
        ("null", None),
        ("", None),
        (None, None),
        ("2.5-for-1.1", "2.5:1.1"),
        ("2.5-for-1.0 split", "2.5:1.0"),
        ("1.5 to 1", "1.5:1"),
        ("3.0:2.5", "3.0:2.5"),
    ],
)
def test_normalize_ratio_valid_cases(input_ratio, expected):
    """Test ratio normalization with valid input formats."""
    assert normalize_ratio(input_ratio) == expected


@pytest.mark.parametrize(
    "invalid_ratio",
    [
        "invalid ratio",
        "2 for",
        "for 1",
        "2-3-4",
        "abc-def",
    ],
)
def test_normalize_ratio_invalid_cases(invalid_ratio):
    """Test ratio normalization raises ValueError for invalid formats."""
    with pytest.raises(ValueError, match="Unable to normalize ratio string"):
        normalize_ratio(invalid_ratio)


@pytest.mark.parametrize(
    "input_date,expected",
    [
        ("2021-06-03", "2021-06-03"),  # Already ISO
        ("2007-09-10", "2007-09-10"),  # Already ISO
        ("06/03/2021", "2021-06-03"),  # MM/DD/YYYY
        ("03/06/2021", "2021-03-06"),  # MM/DD/YYYY
        ("2021/06/03", "2021-06-03"),  # YYYY/MM/DD
        ("June 3, 2021", "2021-06-03"),  # Month DD, YYYY
        ("Jun 3, 2021", "2021-06-03"),  # Mon DD, YYYY
        ("3 June 2021", "2021-06-03"),  # DD Month YYYY
        ("3 Jun 2021", "2021-06-03"),  # DD Mon YYYY
        ("not specified", None),
        ("null", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_date_valid_cases(input_date, expected):
    """Test date normalization with valid input formats."""
    assert normalize_date(input_date) == expected


@pytest.mark.parametrize(
    "invalid_date",
    [
        "invalid date",
        "32/13/2021",
        "2021-13-45",
        "not a date",
        "2021",
        "June 32, 2021",
    ],
)
def test_normalize_date_invalid_cases(invalid_date):
    """Test date normalization raises ValueError for invalid formats."""
    with pytest.raises(ValueError, match="Unable to normalize date string"):
        normalize_date(invalid_date)
