from datetime import date
from decimal import Decimal
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from fastapi import APIRouter, Query
from .schemas import ConvertRequest, ConvertResponse
from .service import process_conversion

router = APIRouter()

@router.get("/convert", response_model=ConvertResponse)
async def convert_currency(
    amount: Decimal,
    from_currency: str = Query(..., alias="from"),
    to_currency: str = Query(..., alias="to"),
    asked_date: date = Query(..., alias="date"),
):
    try:
        request = ConvertRequest(
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
            asked_date=asked_date,
        )
    except ValidationError:
        return JSONResponse(status_code=400, content={"error": "INVALID_INPUT"})

    return await process_conversion(request)