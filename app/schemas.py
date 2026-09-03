from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ErrorCode(str, Enum):
    INVALID_INPUT = "INVALID_INPUT"
    UNSUPPORTED_CURRENCY = "UNSUPPORTED_CURRENCY"
    SAME_CURRENCY = "SAME_CURRENCY"
    RATE_UNAVAILABLE = "RATE_UNAVAILABLE"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class ConvertRequest(BaseModel):
    """Validates incoming query parameters."""
    amount: Decimal = Field(..., gt=0)
    from_currency: str = Field(..., alias="from", pattern=r"^[A-Z]{3}$")
    to_currency: str = Field(..., alias="from", pattern=r"^[A-Z]{3}$")
    asked_date: date = Field(..., alias="date")

    @field_validator("amount")
    @classmethod
    def validate_amount_decimals(cls, v: Decimal) -> Decimal:
        # Check if the amount has 10 or more decimal places
        if abs(v.as_tuple().exponent) >= 10:
            raise ValueError("Amount cannot have 10 or more decimal places.")
        return v

    @field_validator("asked_date")
    @classmethod
    def validate_date_not_in_future(cls, v: date) -> date:
        # Reject future-dated requests, rates aren't available yet
        if v > datetime.now(timezone.utc).date():
            raise ValueError("Date cannot be in the future.")
        return v


class ConvertResponse(BaseModel):
    """Conversion endpoint response schema."""
    amount: Decimal
    from_currency: str = Field(..., serialization_alias="from")
    to_currency: str = Field(..., serialization_alias="to")
    rate: Decimal
    result: Decimal
    rate_date: date
    asked_date: date
    source: str = "ECB via frankfurter.dev"

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "amount": 250,
                "from": "EUR",
                "to": "TRY",
                "rate": 47.1234,
                "result": 11780.85,
                "rate_date": "2026-08-28",
                "asked_date": "2026-08-28",
                "source": "ECB via frankfurter.dev",
            }
        },
    )


class ErrorResponse(BaseModel):
    """Structured error payload format."""
    error: ErrorCode
    message: str


class FrankfurterResponse(BaseModel):
    """Schema representing the raw payload returned by api.frankfurter.dev."""
    amount: Decimal
    base: str
    date: date
    rates: Dict[str, Decimal]