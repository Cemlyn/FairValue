"""
Test fields required for intrinsic value calculation, that is:
- net cash from continuing operations
- capital expenditure (payments for property, plant and equipment)
"""

import pytest
from pydantic import (
    ValidationError,
)
from fairvalue.models.ingestion import (
    Dei,
)