import pytest

import pandas as pd
from pydantic import ValidationError

from fairvalue import Stock


# def test_invalid_ticker_exchange():

#     with pytest.raises(
#         ValidationError,
#     ):
#         Stock(ticker_id='TEST',exchange=['NASDAQY'],cik='123ABC',latest_shares_outstanding=3200,entity_name='test corp',)
