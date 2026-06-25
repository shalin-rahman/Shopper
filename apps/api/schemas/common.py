from __future__ import annotations
from datetime import date, datetime
from typing import Any, Annotated
from pydantic import BeforeValidator, PlainSerializer

def parse_date(v: Any) -> date:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(v.strip(), fmt).date()
            except ValueError:
                pass
    raise ValueError("Invalid date format, expected dd-MM-yyyy or YYYY-MM-DD")

FormattedDate = Annotated[
    date,
    BeforeValidator(parse_date),
    PlainSerializer(lambda v: v.strftime("%d-%m-%Y"), return_type=str),
]
