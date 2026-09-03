# Notes

## Decisions

- **Exact Precision Math:** Used Python's `Decimal` type with `ROUND_HALF_UP` quantization at 4 decimal places for all conversion calculations to completely avoid floating-point drift.
- **Timezone-Aware Publication Boundaries (Europe/Berlin):** Normalized reference time to the ECB's local timezone (`Europe/Berlin`) rather than server local time or UTC. This ensures reliable detection of "same-day" requests and prevents edge cases around the ECB's daily publication window (~16:00 CET), accurately determining whether today's provisional reference rate has been released yet.
- **Weekend & Holiday Handling (`rate_date` vs. `asked_date`):** When the ECB publishes no rate for a requested date (weekends or holidays), the service relies on the upstream provider's fallback to the most recent prior published rate. Rather than hiding this, the response explicitly preserves both `asked_date` and `rate_date` so the consumer/agent can transparently see which day's rate is actually applied.
- **ECB Lifecycle-Aware Caching:** Immutable historical rates are cached indefinitely, while current-day provisional rates use a 5-minute TTL to balance freshness with upstream rate-limit protection.
- **Strict Validation Boundary:** Blocked future dates, dates prior to the ECB series inception (`1999-01-04`), and invalid amounts (amounts <= 0 or with >= 10 decimal places) at the Pydantic validation layer before reaching the network/service layer.

## With Another Day

- **Larger End-to-End Test Suite:** Extend test coverage beyond unit mocks to include contract testing and integration tests against real upstream responses.
- **Real caching instead of in-memory:** Transition from in-memory caching to an external Redis cluster.
- **Observability:** Instrument the service with structured logging and Prometheus metrics.

## AI Tools

- **Claude Code & Gemini:** Used them as thought partners to debate ideas and design choices, write boilerplate and handle edge cases under my manual oversight and code review.

## Challenges & Post-Mortem (What Went Wrong)

- **FastAPI DI vs. Test Fixtures:** AI initially suggested wrapping query parameter validation and schema parsing inside FastAPI's `Depends()` abstraction. This introduced unexpected state-coupling and fixture-override issues when mocking upstream dependencies in the test suite.
- **The Resolution:** After finding the root cause of the test breakage, I refactored the flow from DI to explicit, manuel validation. This resolved the test issues immediately and turned them green. However, debugging this framework-specific lifecycle quirk problem significant time, which prevented completing the remaining tasks of the case (such as polishing the README/NOTES and conducting a final review of tool.py) within the 2.5-hour window.
