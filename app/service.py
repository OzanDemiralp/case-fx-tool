from decimal import Decimal, ROUND_HALF_UP
from .schemas import ConvertRequest, ConvertResponse
from .client import fetch_exchange_rate
from .exceptions import SameCurrencyException, RateUnavailableException

async def process_conversion(request: ConvertRequest) -> ConvertResponse:
    """
    Handles the core business logic of the currency conversion.
    Executes precise decimal math and maps dates appropriately.
    """
    from_curr = request.from_currency
    to_curr = request.to_currency

    # 1. Prevent redundant conversions
    if from_curr == to_curr:
        raise SameCurrencyException(currency=from_curr)

    # 2. Fetch the upstream data
    upstream_data = await fetch_exchange_rate(
        asked_date=request.asked_date,
        from_currency=from_curr,
        to_currency=to_curr
    )

    # 3. Extract the specific rate
    if to_curr not in upstream_data.rates:
        # Safeguard: Frankfurter returned 200, but the target currency is missing from the payload
        raise RateUnavailableException(
            message=f"Rate for {to_curr} was not returned by the ECB for date {upstream_data.date.isoformat()}."
        )
    
    rate = upstream_data.rates[to_curr]

    # 4. Perform exact currency math
    # Currency calculations must strictly avoid floating point artifacts.
    raw_result = request.amount * rate
    
    # Round to 4 decimal places, using ROUND_HALF_UP
    result = raw_result.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    # 5. Construct the validated response
    return ConvertResponse(
        amount=request.amount,
        from_currency=from_curr,
        to_currency=to_curr,
        rate=rate,
        result=result,
        rate_date=upstream_data.date,  # The actual date the ECB published the rate
        asked_date=request.asked_date  # The date requested by user
    )