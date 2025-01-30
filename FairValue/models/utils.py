from datetime import (
    datetime,
)
from typing import (
    Optional,
)


def validate_date(field_name: str, value: Optional[str]) -> str:
    if not value or not value.strip():
        raise ValueError(f"'{field_name}' cannot be None, empty, or blank.")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"Invalid Date field. '{field_name}' must be of the format 'YYYY-MM-DD'."
        )
    return value
