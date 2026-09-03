# Review of tool.py

One page. Findings **ranked** — most harmful to a customer first.

For each finding: what is wrong, what it does to a customer (not to a linter),
and how you would verify it.

## 1.

- **What is wrong:** Cache key ignores the date. The dictionary cache only uses the currency pair as the key.
- **What it does to a customer:** If someone searches for the rate at 2010-01-01, that old rate gets saved under "EUR-TRY". The next user asking for another date's conversion gets the 2010 rate instead of current market data.
- **How to verify:** It could be verified by calling `/tools/convert?from_=EUR&to=TRY&on=2020-01-02` and `/tools/convert?from_=EUR&to=TRY`. Second call will return the 2020 rate.

## 2.

- **What is wrong:** The route wraps everything in a blanket except Exception and returns a standard dictionary with rate: 0.0 and result: 0.0 instead of letting an HTTP 4xx or 5xx error bubble up.
- **What it does to a customer:** Even if user input is invalid, upstream is down etc.; AI agent will get a 200 response code and give the user back something like "your 200 EUR is equal to 0 ZZZs".
- **How to verify:** To verify this we could send something like `/tools/convert?from_=EUR&to=FAKE`, and instead of an error code we would receive a HTTP 200 with a result of 0.0 at the response payload.

## 3.

- **What is wrong:** Code lies about returning the asked date's rates.
- **What it does to a customer:** For example if the user asked for the rates at sunday, instead of returning the friday date Frankfurter normally would've sent, service returns 'here is the rate for sunday'.
- **How to verify:** To verify this we could send a request to the service at a sunday date, and then send the same request to the Frankfurter API and compare the responses.

## The one I would fix before shipping tonight

- I think the most urgent problem is the caching problem. All 3 bugs I listed above must be fixed before production but giving users a years old cached rate looks like the most urgent and destructive one.

## Things that look suspicious but are fine

- **The fallback request to `/latest` when the requested date returns no rates:**
  - It looks suspicious because sending a second HTTP request inside the same function is not a clean way to handle an error.
  - But it is actually fine, because ECB does not publish currency rates on weekends and holidays. Falling back to the latest published rate actually works.
