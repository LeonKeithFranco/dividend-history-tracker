# Dividend history API

A FastAPI service that scrapes, caches, and serves dividend histories for US stocks, with a Streamlit lookup client.

## What problem this solves

This app makes it easier to access dividend information. This service scrapes dividend history from [DividendHistory.org](https://dividendhistory.org/), caches it in SQLite with 7- and 30-day staleness thresholds, and exposes it through a REST API. The scraper is built for reliability; it implements retry logic, exponential backoff, and failure-mode tests. This solves the problem of scraping the page not just once, but scraping it reliably over multiple times.

## Architecture

The project is split into two services that communicate over HTTP:

**Backend (FastAPI)** with three layers:

- **Scraper:** Selenium-driven, fetches and parses dividend pages with retry logic. The fetch and parse steps are separated where Selenium retrieves the HTML and BeautifulSoup parses it. Parsing can be tested against saved fixtures. Pagination is handled automatically.
- **Database:** SQLAlchemy async models backed by SQLite via aiosqlite, with Alembic migrations.
- **API:** FastAPI endpoints with Pydantic response schemas, dependency-injected sessions, and background refresh.

**Frontend (Streamlit)**: A thin lookup client that calls the backend via httpx. No direct imports from the backend; the two are kept separate as distinct uv workspace members.

**Data flow:**

1. User enters ticker
2. Streamlit calls `GET /dividends/{ticker}`
3. API checks SQLite cache
4. if fresh, return cached; if stale, return cached + background refresh; if expired or missing, block on scrape, cache, then return results

## Running locally

Prerequisites: Python 3.12+, uv, Chrome

1. Clone the repo
2. Install dependencies: `uv sync --all-packages`
3. Apply database migrations (from `backend/`): `uv run alembic upgrade head`
4. Start the backend (from `backend/`): `uv run fastapi dev app/main.py`
5. In a second terminal, start the frontend (from `frontend/`): `uv run streamlit run main.py`
6. Open http://localhost:8501 and enter a ticker symbol

The first request for any ticker will take a few seconds. Subsequent requests return cached data immediately.

## API

### GET /dividends/{ticker}

Returns the full dividend history for a US stock. The ticker is case-insensitive (`aapl` and `AAPL` return the same result).

**Response (200):** `company_name`, `ticker_symbol`, `exchange`, `date_refreshed`, and `events`

- `events` are a list of `{ ex_dividend_date, payout_date, cash_amount, pct_change }`
- `cash_amount` is a decimal string with 6 decimal places (e.g. `"0.270000"`), since split-adjusted historical dividends can be fractions of a cent

**Cache behaviour:**

- Fresh (<7 days): returns cached data immediately
- Stale (7-30 days): returns cached data, then triggers background refresh
- Expired (30+ days) or missing: blocks on live scrape, then returns results

**Error response:**

- 404: ticker not found or has no dividend history
- 502: data source returned an unparseable response
- 503: data source unavailable
- 504: data source timed out

FastAPI also generates interactive docs at `http://localhost:8000/docs`

## Testing

The test suite is split by scope:

**Unit tests** (`backend/tests/unit/scraper/`): Scraper reliability tests. The scraper's fetch and parse layers are separated so parsing can be tested against a saved HTML fixture (a downloaded copy of the AAPL page served by a local `http.server`) without the network. Failure-mode tests mock Selenium to simulate timeouts, driver crashes, and stale DOM elements, then verify the correct domain exception surfaces with the correct retry behaviour. A live-marked test (`pytest -m live`) scrapes the real Coca-Cola page as a smoke test.

**Integration tests** (`backend/tests/integration/`): API endpoint tests via FastAPI's `TestClient`. An in-memory SQLite database is created per test. The scraper is mocked at the service boundary so no browser starts. Tests verify cache-miss, cache-hit, and exception throwing.

### Running tests:

- Run all tests: `uv run pytest`
- Run only unit tests: `uv run pytest backend/tests/unit/`
- Run only integration tests: `uv run pytest backend/tests/integration/`
- Run live smoke test: `uv run pytest -m live`
- Run all tests without live smoke test: `uv run pytest -m "not live"`

## Reliability

Scraping web pages is inherently unreliable. The scraper translates Selenium's generic exceptions into domain-specific errors based on which operation failed:

| Operation              | Selenium raises                              | Scraper raises            | Retry?                        |
| ---------------------- | -------------------------------------------- | ------------------------- | ----------------------------- |
| Page load              | `TimeoutException`                           | `ScraperTimeoutError`     | Yes (3×, exponential backoff) |
| Page load              | `WebDriverException`                         | `ScraperUnavailableError` | Yes (3×, exponential backoff) |
| Stock info element     | `TimeoutException`                           | `TickerNotFoundError`     | No                            |
| Metrics element        | `TimeoutException`                           | `TickerHasNoDividends`    | No                            |
| Metrics values         | — (values present but unparsable, e.g. `--`) | `ParseError`              | No                            |
| Dividend history table | `TimeoutException`                           | `TickerHasNoDividends`    | No                            |
| Any element read       | `StaleElementReferenceException`             | `ParseError`              | Yes (3×)                      |

Page-load retries use exponential backoff (2 s, then 4 s); stale-element retries are immediate. Non-retryable errors fail immediately.

The API layer translates these domain exceptions into HTTP status codes via FastAPI exception handlers, so no Selenium-specific details leak through the API boundary. An unhandled exception catch-all returns 500.

## Design decisions

- **Selenium over plain HTTP:** DividendHistory.org renders its tables via JavaScript, so a plain HTTP request gets an empty page. Selenium was chosen for existing fluency from QA background.
- **Fetch/parse separation:** Selenium fetches HTML, BeautifulSoup parses it. This means parsing logic doesn't depend on any browser API and can be tested against saved HTML fixtures instead of the live site.
- **SQLite over Postgres:** Sufficient for a single-user portfolio project. The async driver (`aiosqlite`) keeps it compatible with FastAPI's async endpoints.
- **Cache staleness thresholds (7/30 days):** Most US dividends are announced quarterly (some monthly). For quarterly payers, a 30-day expiry guarantees at least one refresh per announcement cycle. The 7-day fresh window prevents redundant background refreshes.
- **uv workspace layout:** Backend and frontend are separate workspace members with independent dependency groups. The frontend doesn't import backend code and communicates with it only over HTTP.
- **No authentication:** This is a public-data API; auth adds complexity and is out of scope for what this project aims to do.

## Limitations & future work

**Known limitations (v1):**

- Single data source (DividendHistory.org) without a fallback if the site goes down
- Selenium is used even though Playwright would be faster and lighter; chosen deliberately to leverage existing QA fluency
- No circuit breaker — repeated failures to the data source don't throttle future requests
- Cache refreshes (background and blocking) update events only, not metrics
- Coverage is US stocks (NYSE/NASDAQ) only; multi-market support (TSX, LSE) would require handling ticker collisions and currency differences
- No CI/CD pipeline or containerized deployment yet (Podman Compose file exists but is a work in progress)
- Estimated (unconfirmed) upcoming dividends shown on DividendHistory.org are stored and returned alongside confirmed history, with no flag to distinguish them. If the declared date or amount later differs from the estimate, the estimated row is not corrected on refresh
- Stocks that have suspended their dividend (e.g. INTC) return 502 because the metrics table contains no values, even though their past dividend history exists on the source page

**v2 extensions:**

- Summary endpoint (`GET /dividends/{ticker}/summary`) with computed growth rate and payout frequency
- `POST /refresh/{ticker}` endpoint for explicit cache refresh
- Containerized deployment via Podman/Docker Compose
- CI via GitHub Actions
- Deployment to Fly.io
- Playwright migration for faster, lighter scraping
- Flag estimated dividends with an `is_estimate` field and replace stored estimates on each refresh, so upcoming payouts stay visible without mixing into confirmed history

## Lessons learned

- **Fetch/parse separation is non-negotiable for testability.** The scraper's architecture where Selenium fetches HTML, BeautifulSoup parses it, meant parsing could be tested against a saved copy of the page rather than the live site, so tests don't depend on the network or on the site's current data.
- **Mocking at the right seam matters.** Mocking Selenium's `WebDriver` directly is brittle. Wrapping it in `SeleniumWrapper` and mocking at the page-object level (`DividendHistoryPage`) gave stable, readable tests.
- **Exception translation is where domain knowledge lives.** The same `TimeoutException` means different things depending on which element timed out — the whole page (site is down) vs. the stock info element (ticker doesn't exist). The scraper's job is to add that context before the exception leaves the module.
- **Async SQLAlchemy has sharp edges.** Lazy relationship loading silently crashes in async contexts (`MissingGreenlet`). `selectinload`/`contains_eager` must be explicit on every query that touches relationships. The repository layer calls `refresh()` after flushes to ensure loaded relationships are available for Pydantic serialization.
