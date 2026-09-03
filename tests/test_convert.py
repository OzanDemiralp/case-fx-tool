from unittest.mock import patch
from zoneinfo import ZoneInfo
from datetime import date, datetime, timedelta

import httpx
import pytest
import respx
from httpx import Response
from fastapi.testclient import TestClient

from app.main import app
from app.client import _cache, _is_rate_published
from app.constants import ECB_TZ

client = TestClient(app)

# --- DYNAMIC TEST DATES ---
TODAY = datetime.now(ECB_TZ).date()
YESTERDAY = TODAY - timedelta(days=1)

# Find the most recent Sunday, and the Friday before it
days_since_sunday = TODAY.weekday() + 1
LAST_SUNDAY = TODAY - timedelta(days=days_since_sunday)
LAST_FRIDAY = LAST_SUNDAY - timedelta(days=2)

@pytest.fixture(autouse=True)
def clear_cache():
    """Ensure a clean cache before every test."""
    _cache.clear()
    yield

@respx.mock
def test_successful_conversion_exact_date():
    """Test standard conversion where asked date matches the ECB published date."""
    respx.get(url__regex=rf".*/v1/{YESTERDAY.isoformat()}").mock(
        return_value=Response(
            200, 
            json={
                "amount": 1.0,
                "base": "EUR",
                "date": YESTERDAY.isoformat(),
                "rates": {"TRY": 47.1234}
            }
        )
    )

    response = client.get(f"/convert?amount=250&from=EUR&to=TRY&date={YESTERDAY.isoformat()}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["result"] == "11780.8500" 
    assert data["rate_date"] == YESTERDAY.isoformat()
    assert data["asked_date"] == YESTERDAY.isoformat()

@respx.mock
def test_weekend_date_fallback():
    """Test asking for a Sunday. Upstream returns Friday. Service must show the difference."""
    respx.get(url__regex=rf".*/v1/{LAST_SUNDAY.isoformat()}").mock(
        return_value=Response(
            200, 
            json={
                "amount": 1.0,
                "base": "EUR",
                "date": LAST_FRIDAY.isoformat(),  # Returns Friday
                "rates": {"TRY": 47.1234}
            }
        )
    )

    response = client.get(f"/convert?amount=100&from=EUR&to=TRY&date={LAST_SUNDAY.isoformat()}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["asked_date"] == LAST_SUNDAY.isoformat()
    assert data["rate_date"] == LAST_FRIDAY.isoformat()

@respx.mock
def test_upstream_malformed_response():
    respx.get(url__regex=rf".*/v1/{YESTERDAY.isoformat()}").mock(
        return_value=Response(200, content=b"not json")
    )
    response = client.get(f"/convert?amount=100&from=EUR&to=TRY&date={YESTERDAY.isoformat()}")
    assert response.status_code == 502
    assert response.json()["error"] == "UPSTREAM_ERROR"

def test_validation_future_date():
    response = client.get("/convert?amount=100&from=EUR&to=TRY&date=2099-01-01")
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_INPUT"

def test_validation_date_before_ecb_series():
    response = client.get("/convert?amount=100&from=EUR&to=TRY&date=1990-01-01")
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_INPUT"

@respx.mock
def test_caching_prevents_duplicate_upstream_calls():
    mock_route = respx.get(url__regex=rf".*/v1/{YESTERDAY.isoformat()}").mock(
        return_value=Response(
            200, 
            json={"amount": 1.0, "base": "EUR", "date": YESTERDAY.isoformat(), "rates": {"TRY": 47.1234}}
        )
    )

    client.get(f"/convert?amount=100&from=EUR&to=TRY&date={YESTERDAY.isoformat()}")
    client.get(f"/convert?amount=100&from=EUR&to=TRY&date={YESTERDAY.isoformat()}")

    assert mock_route.call_count == 1

def test_validation_same_currency():
    response = client.get(f"/convert?amount=100&from=EUR&to=EUR&date={YESTERDAY.isoformat()}")
    assert response.status_code == 400
    assert response.json()["error"] == "SAME_CURRENCY"

def test_validation_negative_amount():
    response = client.get(f"/convert?amount=-50&from=EUR&to=TRY&date={YESTERDAY.isoformat()}")
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_INPUT"

@respx.mock
def test_upstream_unavailable_500():
    respx.get(url__regex=r".*/v1/.*").mock(return_value=Response(500))
    response = client.get(f"/convert?amount=100&from=EUR&to=TRY&date={YESTERDAY.isoformat()}")
    assert response.status_code == 502 

@respx.mock
def test_unsupported_currency():
    respx.get(url__regex=rf".*/v1/{YESTERDAY.isoformat()}").mock(
        return_value=Response(404, json={"message": "not found"})
    )
    response = client.get(f"/convert?amount=100&from=EUR&to=ZZZ&date={YESTERDAY.isoformat()}")
    assert response.status_code == 404
    assert response.json()["error"] == "UNSUPPORTED_CURRENCY"

@respx.mock
def test_upstream_timeout():
    respx.get(url__regex=r".*/v1/.*").mock(side_effect=httpx.TimeoutException("timed out"))
    response = client.get(f"/convert?amount=100&from=EUR&to=TRY&date={YESTERDAY.isoformat()}")
    assert response.status_code == 504
    assert response.json()["error"] == "UPSTREAM_TIMEOUT"

@patch("app.client.datetime")
def test_is_rate_published_boundary(mock_datetime):
    # Simulated date for logic boundaries, completely detached from actual clock
    mock_datetime.now.return_value = datetime(2026, 9, 3, 15, 0, tzinfo=ECB_TZ)
    
    assert _is_rate_published(date(2026, 9, 2)) is True
    assert _is_rate_published(date(2026, 9, 3)) is False
    
    mock_datetime.now.return_value = datetime(2026, 9, 3, 16, 30, tzinfo=ECB_TZ)
    assert _is_rate_published(date(2026, 9, 3)) is True

    mock_datetime.now.return_value = datetime(2026, 9, 3, 16, 0, tzinfo=ECB_TZ)
    assert _is_rate_published(date(2026, 9, 3)) is True  


@respx.mock
@patch("app.client.datetime")
@patch("app.client.time")
def test_provisional_cache_expires_and_refetches(mock_time, mock_datetime):
    mock_datetime.now.return_value = datetime(2026, 9, 3, 15, 0, tzinfo=ECB_TZ)  # pre-publish

    mock_route = respx.get(url__regex=r".*/v1/2026-09-03").mock(
        return_value=Response(200, json={"amount": 1.0, "base": "EUR", "date": "2026-09-03", "rates": {"TRY": 47.0}})
    )

    mock_time.time.return_value = 1000.0
    client.get("/convert?amount=100&from=EUR&to=TRY&date=2026-09-03")
    assert mock_route.call_count == 1

    mock_time.time.return_value = 1000.0 + 100
    client.get("/convert?amount=100&from=EUR&to=TRY&date=2026-09-03")
    assert mock_route.call_count == 1

    mock_time.time.return_value = 1000.0 + 301
    client.get("/convert?amount=100&from=EUR&to=TRY&date=2026-09-03")
    assert mock_route.call_count == 2