# FX Converter Tool for AI Agents

A robust, production-ready currency conversion HTTP service built with **Python & FastAPI**, designed to be called safely by AI agents. It uses European Central Bank (ECB) rates via the public [Frankfurter API](https://api.frankfurter.dev).

---

## Quick Start

### Prerequisites

- Python 3.10+
- A virtual environment (`venv`) set up in the root directory.

### Running the Service

The service uses `./run.sh` as required. It respects the following environment variables:

- `PORT` (default: `8080`)
- `FX_UPSTREAM_BASE` (default: `https://api.frankfurter.dev`)

```bash
# Start the service using the provided script
./run.sh

```

---

## Running Tests

The test suite runs completely offline by mocking the upstream HTTP client, ensuring tests pass with zero network dependency.

```bash
# Run tests using the provided script
./test.sh

```

---

## API Endpoint

### `GET /convert`

**Query Parameters:**

- `amount` (float, required): The amount to convert (must be > 0, max 9 decimal places).
- `from` (string, required): Source 3-letter currency code (e.g., `EUR`).
- `to` (string, required): Target 3-letter currency code (e.g., `TRY`).
- `date` (string, required): Target date in `YYYY-MM-DD` format.

**Success Response (`200 OK`):**

```json
{
  "amount": 250,
  "from": "EUR",
  "to": "TRY",
  "rate": 47.1234,
  "result": 11780.85,
  "rate_date": "2026-08-28",
  "asked_date": "2026-08-28",
  "source": "ECB via frankfurter.dev"
}
```

---

## Edge Case Handling

Since this service feeds data to an AI agent talking to paying customers, accuracy and transparency are prioritized over guesswork:

1. **Weekends & Holidays (No Rate Published):**

- The ECB does not publish rates on weekends or public holidays. The upstream Frankfurter API natively resolves this by returning the most recently available prior published rate. Our service captures this and exposes the exact distinction via `rate_date` (the actual rate day) versus `asked_date` (what the caller requested) so the model can inform the user transparently.

2. **Future Dates / Out-of-Range Dates:**

- Requests with future dates or dates preceding the ECB series start (`1999-01-04`) are validated and rejected upfront. Rates are never invented.

3. **Invalid or Identical Currencies:**

- If `from` and `to` are identical, or if a currency code is unrecognized, the request is safely rejected with a descriptive error.

4. **Upstream Failures & Timeouts:**

- Timeouts, 500-level errors, or malformed/non-JSON payloads from the upstream are caught and mapped safely to clean downstream error responses.

5. **Amount Validation:**

- Missing, zero, negative, or excessively granular amounts (10+ decimal places) are blocked at the request validation layer.

6. **Smart Caching:**

- Historical rates are cached indefinitely (as they are immutable), while provisional/current-day rates use a 5-minute TTL to balance freshness and rate limits.

## Error Codes

When a request fails, the service returns a non-2xx status code alongside a structured JSON error body containing a machine-readable code and a human-readable message.

- **`INVALID_INPUT`** (`400 Bad Request`)
  Missing parameters, malformed query syntax, invalid amounts (less than or equal to 0, or 10 or more decimals), or invalid dates (future dates or pre-1999).
- **`SAME_CURRENCY`** (`400 Bad Request`)
  The `from` and `to` currency codes are identical.
- **`UNSUPPORTED_CURRENCY`** (`404 Not Found`)
  The requested currency code is unrecognized or unsupported by the upstream provider.
- **`RATE_UNAVAILABLE`** (`404 Not Found`)
  No historical rate data could be found for the target currency on the requested date.
- **`UPSTREAM_TIMEOUT`** (`504 Gateway Timeout`)
  The upstream Frankfurter API request timed out.
- **`UPSTREAM_ERROR`** (`502 Bad Gateway`)
  The upstream API returned a 5xx server error, unexpected status code, or malformed non-JSON data.
