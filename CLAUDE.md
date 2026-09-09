# fotowa-automation-project — context for Claude

End-to-end UI test suite for **fotowa** (staging/review env), written in **Playwright Python +
pytest** using the Page Object Model. README.md is written in Vietnamese; the user is a QA/SDET
working from Windows 11 + PowerShell.

## Stack & runtime facts

| Thing | Value |
|---|---|
| Python | 3.13, venv at `.venv` (native Windows CPython — do **not** reuse a Linux venv here) |
| Deps | `pytest==8.3.4`, `pytest-playwright==0.6.2`, `python-dotenv==1.0.1`, `pyright==1.1.411` (`requirements.txt`) |
| Browser | **Installed Google Chrome**, via `channel="chrome"`, `headless=False`. Bundled Chromium is not used |
| Env manager | `uv` (`uv venv --python 3.13 --seed`, `uv pip install -r requirements.txt`) |

Run tests (PowerShell, from repo root):

```powershell
.venv\Scripts\python.exe -m pytest                      # no activation needed
.venv\Scripts\python.exe -m pytest --headed --slowmo 500
.venv\Scripts\python.exe -m pytest tests/test_login.py::test_01_login_form_is_displayed
.venv\Scripts\python.exe scripts\check.py               # static checks, no browser
```

`pytest.ini`: `-v --browser chromium --screenshot only-on-failure --tracing retain-on-failure`,
`testpaths = tests`, `pythonpath = .`, plus a `markers` entry registering `incremental` (see
*Conventions* below).

`scripts/check.py` runs the two static gates and exits non-zero if either fails:
`pytest --setup-plan -q` (resolves every fixture without opening a browser — the only way to catch a
misspelled fixture name, since fixtures match by string at runtime) and `pyright`
(`pyrightconfig.json`: basic mode over `pages`, `tests`, `scripts`; same engine as Pylance). Run it
before a browser run — seconds instead of minutes.

## Layout

```
pages/login.py                       LoginPage: header ログイン link + email/password form + login-state assertions
pages/photographer_profile.py        PhotographerProfilePage + BookingSlot dataclass (calendar)
pages/booking_request.py             BookingRequestPage (post-slot-click page; locators confirmed)
tests/conftest.py                    dotenv, session fixtures, `logged_in` gate
tests/test_login.py                  2 tests
tests/test_photographer_profile.py   3 tests
scripts/save_auth.py                 One-time manual Google SSO -> .auth/storage_state.json
scripts/check.py                     --setup-plan + pyright in one command
pyrightconfig.json                   Type-check config
.env.example                         Committed template; .env and .auth/ are gitignored
fixtures/booking_calendar.html       Committed: saved DOM of the calendar, for writing XPath offline
```

## Auth model (the central constraint)

Two separate gates — don't confuse them:

1. **The staging front door** is behind **Google SSO (AWS Cognito → Google IdP)**, not automatable.
   Run `.venv\Scripts\python.exe scripts\save_auth.py` once. It opens Chrome with a dedicated
   persistent profile (`.auth/chrome-profile`), waits (default 300s, `GOOGLE_SSO_LOGIN_TIMEOUT_MS`)
   for a redirect back to `BASE_URL`'s host (excluding `/oauth2/*`), then dumps
   `.auth/storage_state.json`. `conftest.browser_context` loads that state if the file exists
   (absent is tolerated — tests that only view the login page still work).
2. **The fotowa app login** at `/users/sign_in` *is* a normal email/password form, and the tests
   drive it. The `logged_in` session fixture does this once per run: `goto_home_page()`,
   short-circuit if `is_logged_in()`, otherwise `goto_login_page()` → `login(email, password)` →
   `expect_logged_in()`.

Why a separate Chrome profile and not the user's real one: Chrome 136+ refuses remote debugging on
the default user-data-dir, and App-Bound Encryption makes copied cookies undecryptable.

## Environment variables

Loaded from `.env` via `load_dotenv` in both `conftest.py` and `save_auth.py`. Real shell env vars
win over the file.

- `BASE_URL` — **required, no code default**; missing ⇒ `pytest.fail` / `sys.exit`. Template value:
  `https://master.review.fotowa.com`.
- `TEST_EMAIL`, `TEST_PASSWORD` — the `credentials` fixture **skips** if either is empty, and that
  skip cascades through `logged_in` to everything downstream.
- `DEFAULT_TIMEOUT_MS` (30000) — applied in the `page` fixture to action, navigation **and**
  `expect` assertion timeouts (`expect` defaults to 5s and is not affected by the other two).
- `AUTH_DIR` (`.auth`), `AUTH_STATE` (`.auth/storage_state.json`),
  `AUTOMATION_PROFILE_DIR` (`.auth/chrome-profile`), `GOOGLE_SSO_LOGIN_TIMEOUT_MS` (300000).

## Fixtures (all `scope="session"`, in `tests/conftest.py`)

```
base_url → playwright_instance → browser_context → context → page
                                                               ↓
        login_page ──→ credentials ──→ logged_in ──→ photographer_profile_page
                                                     booking_request_page (no logged_in dep)
```

`booking_request_page` deliberately does **not** depend on `logged_in`: that page is only reached by
clicking a calendar slot, so it always runs after an authenticated test.

## Conventions that bite if ignored

**Session-scoped fixtures, shared tab.** The whole run happens in **one tab**, and each test resumes
wherever the previous one left the browser. Consequences:
- Tests in a file run in **declaration order**, and order is load-bearing — hence the `test_01_` /
  `test_02_` / `test_03_` name prefixes. Moving a test changes its starting state.
  `test_02_has_available_date` and `test_03_select_first_available_slot` both rely on
  `test_01_booking_calendar_is_displayed` having navigated to the profile page first.
- Running one test alone starts at `about:blank`, so order-dependent tests fail in isolation.
  pytest never auto-runs the tests that precede it — only **fixtures** are a dependency graph.
  To make a test stand alone, add explicit navigation, or move the precondition into a fixture.

**The `incremental` marker.** `tests/conftest.py` implements the standard pytest recipe with two
hooks (`pytest_runtest_makereport` + `pytest_runtest_setup`) keyed on a module-level
`_failed_in_module` dict: once a test carrying the marker fails, every later test **in the same
module** is skipped with `test trước đó đã fail: <name>` instead of failing in a confusing
cascade. `Skipped` exceptions are filtered out, so the `credentials` skip does not arm it.
`tests/test_photographer_profile.py` opts in via a module-level `pytestmark = pytest.mark.incremental`.
This guards *within* a run only — it still does not let a test run in isolation.

**Overridden `context`/`page` fixtures.** `conftest.py` overrides pytest-playwright's own
`context`/`page` to inject the authenticated context. Side effect: the plugin's `new_context`
fixture is bypassed, so `--screenshot` and `--tracing` in `pytest.ini` currently **produce no
artifacts**. Known, accepted trade-off. To inspect a failure live, run `pytest --pdb` — teardown is
deferred until you exit the debugger, so the Chrome window stays open in the failed state.

**Page objects: no actions in `__init__`.** Declare locators only (lazy `Locator` objects). Fixtures
build page objects while the page may still be `about:blank`, so any `.click()/.fill()` there would
burn a 30s timeout inside the fixture. Method naming: `goto_*` navigate, `expect_*` assert,
everything else acts.

**Strict mode.** Playwright strict mode is on; fotowa renders its header **twice** (desktop +
mobile), so a naive selector hits 2 nodes and raises `strict mode violation`. Anchor to something
unique or add `.first`.

**Locators are XPath and Japanese-text-based** (`text()='ログイン'`, success notice
`ログインに成功しました`). The UI is Japanese.

**Login state is asserted positively, never by absence.** `LoginPage` has three separate members
for it, because one method cannot serve both roles:
- `logged_in_marker` — `//a[@href='/users/sign_out' and @data-ga-label='sign-out']`, the ログアウト
  link the server only renders when authenticated. Matches **2** nodes (desktop header + hamburger)
  and the desktop one sits in a hover dropdown, so it reads `visible=false` — test for
  *attachment*, not visibility, and use `.first` under strict mode.
- `is_logged_in()` — `count() > 0`, no retry. The `logged_in` fixture's short-circuit probe: "not
  logged in" is a normal outcome, so it must not burn `DEFAULT_TIMEOUT_MS`.
- `expect_logged_in()` / `expect_login_success()` — retrying assertions. The latter is the
  post-submit behaviour (URL back to home + `div.globalNotice > p.globalNotice__description`
  showing `ログインに成功しました`) and belongs to `test_02` only; the notice shows once, so the
  fixture uses `expect_logged_in()` instead.

## The booking calendar (the tricky page object)

`PhotographerProfilePage` is pinned to one staging photographer: `PATH = "/photographers/bebe"`.

Calendar `td`s carry **no date or time data** — an `available` cell contains only an icon. Both are
derived from position:
- **hour** = the cell's row index → look up `table.time` at the same index
- **day** = which `table.events` the cell is in (one table per day, 7 columns) → look up
  `tr.dayname` at the same index
- **year/month** = `tr.month` in `table.calendar__header`, formatted `"2026/09"` — but a week
  straddling two months renders **two** `th[@colspan]` (`colspan=3` "2026/09" + `colspan=4`
  "2026/10"), so `_read_year_month(column)` walks the colspans instead of reading one value

`goto_week_with_available_date()` clicks 次週 (`//li[@class='next']/a`) up to `MAX_WEEKS = 4`
times until the visible week has an `available` cell — staging is often fully booked and that
is data, not a bug. It uses `.count()`, not `expect(...).not_to_have_count(0)`, so a booked week
costs one call instead of a full `DEFAULT_TIMEOUT_MS`. The render gate after each click is
`page.wait_for_function` (the day cell must exist **and** differ): `not_to_have_text` passes the
instant Vue detaches the `td` mid-rerender, which returns before the new week is painted.

`select_first_available_slot()` walks the columns, pulls every cell's `className` in one
`evaluate_all` (not one round-trip per cell), clicks the first `available` one, and returns a frozen
`BookingSlot(year, month, day, time)`. Tests assert against that returned value, so no date is ever
hardcoded.

## Current state / open items

- **`pages/booking_request.py` is done and verified green.** `selected_datetime` is
  `//div[@id='app']//div[@class='shootingDateTimeControl__details']`, and `expect_slot` asserts the
  real format in two `to_contain_text` calls: a zero-padded date `2026/09/16` and a time **range**
  `08:00 - 09:00` (`SHOOTING_DURATION = timedelta(hours=1)`). Asserting the end hour too means a
  wrong-cell click can't false-pass. `test_03_select_first_available_slot` passes against staging.
- Still open on the booking flow: assert the destination URL (dynamic path, needs a regex like
  `re.compile(r"/reservations/")` — confirm the real pattern first), and fill in + submit the
  booking form (the suite currently stops at the slot click).
- `LoginPage.expect_error` and `expect_still_on_login_page` exist but no test uses them — there is
  no invalid-credentials test yet.
- `USE_CHROME_PROFILE` in `.env.example` is **dead** — no code reads it.
- `TODO.md` tracks the live backlog (destination-URL assert, submitting the booking form, missing
  invalid-login test, headless/CI). Keep it in sync when an item here is closed.

## Troubleshooting (learned the hard way)

- **`403 Forbidden` from `awselb/2.0`** — a **User-Agent block**, not an IP allowlist, and no VPN is
  needed. Default `curl` gets 403; with a Chrome UA the site returns 200 and redirects to Google SSO.
- **Everything skipped** — `TEST_EMAIL`/`TEST_PASSWORD` are empty in `.env`; the skip in
  `credentials` propagates through `logged_in` to every page test.
- **Timeout waiting for the login form** — you're probably stranded on the Google SSO page; the
  saved session expired. Re-run `scripts/save_auth.py`.
- **`launch_persistent_context` fails / profile locked** — close every Chrome window using
  `.auth/chrome-profile`.
- **`fixture '...' not found`, only at runtime** — run `scripts/check.py`; pyright can't see fixture
  wiring, `--setup-plan` can.

## Working preferences

- Keep replies short and condensed.
- Repo prose (README, code comments) is in **Vietnamese** — match it when editing those files.
- Branch is `master`; upstream main branch is `main`.
