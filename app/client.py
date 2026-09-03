import os
import time
import httpx
from datetime import date, datetime
from typing import Dict, Tuple
from .constants import ECB_TZ
from .schemas import FrankfurterResponse
from .exceptions import (
    UpstreamTimeoutException,
    UpstreamErrorException,
    UnsupportedCurrencyException,
)

http_client = httpx.AsyncClient(timeout=5.0)

FX_UPSTREAM_BASE = os.getenv("FX_UPSTREAM_BASE", "https://api.frankfurter.dev")
PROVISIONAL_TTL_SECONDS = 300
MAX_CACHE_SIZE = 1000
# Cache format: key -> (FrankfurterResponse, expiration_timestamp_or_None)
_cache: Dict[str, Tuple[FrankfurterResponse, float | None]] = {}


def _is_rate_published(d: date) -> bool:
    """True once ECB's rate for date `d` is finalized and safe to cache indefinitely."""
    now = datetime.now(ECB_TZ)
    if d < now.date():
        return True
    if d == now.date():
        return now.hour >= 16
    return False


async def fetch_exchange_rate(asked_date: date, from_currency: str, to_currency: str) -> FrankfurterResponse:
    cache_key = f"{asked_date.isoformat()}-{from_currency}-{to_currency}"
    now = time.time()

    # 1. Check Cache
    if cache_key in _cache:
        cached_response, expiration = _cache[cache_key]
        if expiration is None or now < expiration:
            return cached_response

    # 2. Fetch from Upstream
    url = f"{FX_UPSTREAM_BASE}/v1/{asked_date.isoformat()}"
    params = {"base": from_currency, "symbols": to_currency}

    try:
        response = await http_client.get(url, params=params)
    except httpx.TimeoutException:
        raise UpstreamTimeoutException()
    except httpx.RequestError as e:
        raise UpstreamErrorException(detail=str(e))

    # 3. Handle Errors
    if response.status_code == 404:
        try:
            msg = response.json().get("message", f"Unrecognized currency: {from_currency} or {to_currency}")
        except Exception:
            msg = f"Unrecognized currency: {from_currency} or {to_currency}"
        raise UnsupportedCurrencyException(currency=msg)
    
    if response.status_code >= 500:
        raise UpstreamErrorException(detail=f"Upstream server returned {response.status_code}")
    if not response.is_success:
        raise UpstreamErrorException(detail=f"Unexpected upstream response: {response.status_code}")

    try:
        data = response.json()
        validated_response = FrankfurterResponse.model_validate(data)
    except Exception:
        raise UpstreamErrorException(detail="Upstream returned malformed or non-JSON data")

    # 4. Save to Cache based on ECB Lifecycle
    if len(_cache) >= MAX_CACHE_SIZE:
        _cache.pop(next(iter(_cache)))

    if _is_rate_published(asked_date):
        _cache[cache_key] = (validated_response, None)  # Cache forever
    else:
        _cache[cache_key] = (validated_response, now + PROVISIONAL_TTL_SECONDS)  # 5-minute TTL

    return validated_response