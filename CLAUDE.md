# fotowa-automation-project — context for Claude

End-to-end UI test suite for **fotowa** (staging), Playwright Python + pytest, Page Object Model.
README.md is in Vietnamese; the user is a QA/SDET on Windows 11 + PowerShell.

## Stack

Python 3.13, venv at `.venv` (native Windows CPython — never reuse a Linux venv).
`pytest==8.3.4`, `pytest-playwright==0.6.2`, `python-dotenv==1.0.1`, `pyright==1.1.411`.
Browser: **installed Google Chrome** via `channel="chrome"`, `headless=False`. Env manager: `uv`.

```powershell
.venv\Scripts\python.exe -m pytest                       # 9 tests, ~50s
.venv\Scripts\python.exe -m pytest -rs                   # -rs: make skips visible
.venv\Scripts\python.exe -m pytest tests/test_user_01_login.py::TC_01_login_form_is_displayed
.venv\Scripts\python.exe scripts\check.py                # static gates, no browser
```

`pytest.ini`: `-v --browser chromium --screenshot only-on-failure`,
`testpaths = tests`, `pythonpath = .`, and
**`python_functions = TC_* test_*`** — tests are named by test-case id (`TC_01_...`); drop that
line and pytest collects nothing.

`scripts/check.py` = two static gates, no browser: `pytest --setup-plan -q` (resolves every
fixture — the only way to catch a misspelled fixture name) and `pyright` (basic mode over `pages`,
`tests`, `scripts`). Run it before any browser run. There is no linter — ruff was removed from the
project; do not reintroduce one without being asked.

## Layout

```
pages/user/login.py                         LoginPage
pages/user/photographer_profile.py          PhotographerProfilePage + BookingSlot (calendar)
pages/user/booking_request.py               BookingRequestPage + ShootingOption (private-offer form)
tests/conftest.py                           dotenv, fixtures, `_sign_in`, `_find_first_available_slot`
tests/test_user_01_login.py                 2 tests
tests/test_user_02_photographer_profile.py  2 tests
tests/test_user_03_booking_request.py       5 tests (slot echo, payment table, long-distance fee)
scripts/save_auth.py                        One-time manual Google SSO
scripts/check.py                            --setup-plan + pyright
fixtures/*.html                             Saved DOM for writing XPath offline — numbers are stale
plan/booking-price-check.md                 Write-up of the payment/fee verification work
plan/booking-confirm-payment.md             Plan for the review + payment page (blocked on its DOM)
plan/independent-tests.md                   Write-up of the test-independence work (steps 1-6 done)
.env.example                                Committed; `.env` and `.auth/` are gitignored
```

## Auth model (the central constraint)

Two separate gates:

1. **Staging front door** — Google SSO (AWS Cognito → Google IdP), not automatable. Run
   `scripts\save_auth.py` once; it signs in through a dedicated persistent Chrome profile
   (`.auth/chrome-profile`). It also writes `.auth/storage_state.json`, which **nothing reads** —
   `conftest.browser_context` uses `launch_persistent_context` on that same profile, so the SSO
   cookies are already in it.
2. **App login** at `/users/sign_in` — a normal email/password form the tests drive. `_sign_in()`
   (a plain function, not a fixture, so any scope can call it): `goto_home_page()` → short-circuit
   if `is_logged_in()` → otherwise `goto_login_page()` → `login()` → `expect_logged_in()`. The
   `logged_in` fixture is a one-line wrapper. Cookies live on the shared `context`, so signing in
   on any tab logs in every tab — that is what keeps the per-test short-circuit cheap.

**Why a persistent profile instead of `new_context(storage_state=...)`:** `assets/bundle/vendor.js`
is 10.5 MB served uncompressed and blocks the parser. Cold cache ⇒ DOMContentLoaded ~110s ⇒ every
run failed on the first `goto`. Warm profile cache ⇒ 1.8s. (A separate profile, not the real one:
Chrome 136+ refuses remote debugging on the default user-data-dir.)

The profile keeps cookies too, so a run would otherwise start already logged in and
`TC_01_login_form_is_displayed` would find no form. The **`logged_out` fixture** clears exactly one
cookie — `_session_id` (the Rails app session) — and the two login tests request it by name.
`AWSELBAuthSessionCookie-0`/`-1` is the SSO door and **must survive**; clearing all cookies strands
the run on Google. (This used to be an unconditional clear inside `browser_context`, which silently
handed the first-collected test a logged-out browser. Now the requirement is in the signature.)

Side effect: `launch_persistent_context` opens its own blank tab; the `page` fixture adds a fresh
tab per test.

## Environment variables

Loaded from `.env` by `conftest.py` and `save_auth.py`; real shell vars win.

- `BASE_URL` — **required, no default**; missing ⇒ `pytest.fail` / `sys.exit`.
- `TEST_EMAIL` / `TEST_PASSWORD` — `credentials` **skips** if either is empty, cascading through
  `logged_in` to everything downstream.
- `PHOTOGRAPHER_NAME` (`bebe`) → `photographer_path` fixture → `/photographers/<slug>`, shared by
  both page objects. **Read it in `conftest.py`, never in a page-object class body:** `conftest`
  imports `pages.*` before `load_dotenv()`, so an `os.getenv` in a class body silently falls back
  to the default.
- `AUTH_DIR` (`.auth`) and `AUTOMATION_PROFILE_DIR` (`.auth/chrome-profile`) — read by both
  `conftest.py` and `save_auth.py`; must resolve to the same profile or the run loses the warm
  cache and the SSO cookies.
- `AUTH_STATE`, `GOOGLE_SSO_LOGIN_TIMEOUT_MS` (300000) — only `save_auth.py`.
- No timeout env var: Playwright defaults (30s action/navigation, 5s `expect`).
- `USE_CHROME_PROFILE` in `.env.example` is **dead** — no code reads it.

## Fixtures (`tests/conftest.py`)

**session** (expensive, no per-test state): `base_url`, `playwright_instance`, `browser_context`,
`context`, `credentials`, `photographer_path`, `available_slot`.
**function** (anything holding a `page`): `page`, `login_page`, `logged_in`, `logged_out`,
`photographer_profile_page`, `booking_request_page`, `selected_slot`.

```
context ──→ page ──→ login_page ──→ logged_in ──→ photographer_profile_page ──→ selected_slot
   │           │                                  booking_request_page (no logged_in dep)
   │           └──→ logged_out  (login tests only)
   └──→ available_slot   (opens and closes its own scratch tab; returns data only)
```

The scope rule is not a preference: a session-scoped fixture cannot request a function-scoped one
(`ScopeMismatch`), so `page → function` forces every page-object fixture to follow.

**`available_slot` vs `selected_slot` — they look alike and are not.**
- `available_slot` (session) is **data**: it opens a scratch tab, signs in, runs
  `_find_first_available_slot`, closes the tab, and returns a frozen `BookingSlot`. It leaves no
  browser state, so nothing can free-ride on it. Tests that need the private-offer page call
  `goto_booking_request(available_slot)` — direct URL, no calendar walk.
- `selected_slot` (function) goes through the **real click path** and leaves the browser on the
  destination page. Only `test_user_03::TC_01` uses it, because that test is the assertion *about*
  the click.

## Conventions that bite if ignored

**Every test owns its tab and navigates itself.** `page` is function-scoped: each test starts at
`about:blank`, so the first line of a test is a `goto_*`. Run order no longer means anything — the
numbers in `TC_01_` / `test_user_01_` are test-case ids, not a contract. Preconditions belong in
fixtures, never in "whatever the previous test left behind"; only **fixtures** form a dependency
graph, tests do not.

Proving it is a separate act from a green suite: run every nodeid on its own.

```powershell
.venv\Scripts\python.exe -m pytest --collect-only -q -o addopts=   # -o addopts= cancels the -v in pytest.ini
```

(The suite used to share one session-scoped tab and needed an `incremental` marker to stop the
cascade. Both are gone — see `plan/independent-tests.md`. Do not reintroduce order coupling.)

**Overridden `context`/`page`.** They inject the authenticated context and bypass the plugin's
`new_context`, which is where pytest-playwright records artifacts — so none of the plugin's own
capture runs. `conftest` replaces the screenshot half: a `pytest_runtest_makereport` wrapper stashes
the failure under `_FAILED`, and the `page` fixture calls `_capture_screenshot()` before closing
the tab, writing a full-page PNG to `<--output>/<nodeid>-{failed,finished}.png` (`test-results/`,
gitignored). It follows the plugin's own `--screenshot` semantics — `on` shoots every test,
`only-on-failure` (the `pytest.ini` default) only the failures, `off` nothing.
**Trace and video are still not produced** — tracing lives on the shared session-scoped context, so
it would need `start_chunk`/`stop_chunk` per test and `available_slot`'s scratch tab would leak into
the chunk; `--tracing` is therefore out of `pytest.ini` rather than
lying. `pytest --pdb` remains the way to inspect a failure live (teardown is deferred, the window
stays open).

**Page objects: no actions in `__init__`** — lazy locators only, or a fixture burns a 30s timeout
on `about:blank`. Naming: `goto_*` navigates, `expect_*` asserts, everything else acts.

**Strict mode is on** and fotowa renders its header twice (desktop + mobile) — anchor to something
unique or add `.first`.

**Locators are XPath + Japanese text** (`ログイン`, `遠方出張料`, `ログインに成功しました`) —
every locator, no CSS. Verified on Chrome: a chained `parent.locator("//x")` **is** scoped to the
parent, so the `//` prefix is safe. But `:visible` is a CSS-only pseudo-class and raises
`SyntaxError` on an XPath — use `.filter(visible=True)` (see `genre_options`). `has_text=` and
`has=` work with XPath unchanged.

**Login state is asserted positively, never by absence.** `logged_in_marker` is the ログアウト link
(`//a[@href='/users/sign_out' and @data-ga-label='sign-out']`); it matches 2 nodes and the desktop
one sits in a hover dropdown, so test for *attachment*, not visibility. `is_logged_in()` is a cheap
`count() > 0` probe (not logged in is a normal outcome — must not burn 30s); `expect_logged_in()`
retries; `expect_login_success()` checks the one-shot `ログインに成功しました` notice and belongs to
the login test only.

**Anything Vue renders needs a retrying `expect()`.** `.all()`, `inner_text()` and `count()` do not
auto-wait; reading a price table straight after a click returns the pre-update DOM.

## The booking calendar

Calendar `td`s carry **no date/time data** — an `available` cell holds only an icon. Everything is
derived from position: **hour** = row index into `table.time`; **day** = which `table.events` the
cell is in, indexed into `tr.dayname`; **year/month** = `tr.month` in `table.calendar__header`, but
a week straddling two months renders two `th[@colspan]`, so `_read_year_month(column)` walks the
colspans.

`goto_week_with_available_date()` clicks 次週 up to `MAX_WEEKS = 10` times — staging is often fully
booked, and that is data, not a bug. It uses `.count()` so a booked week costs one call, not a 30s
timeout. The gate after each click must be `page.wait_for_function` (cell exists **and** differs):
`not_to_have_text` passes the instant Vue detaches the `td` mid-rerender.

`select_first_available_slot()` pulls every cell's `className` in one `evaluate_all`, clicks the
first `available` one, returns a frozen `BookingSlot`. Tests assert on that value — no date is ever
hardcoded.

## Booking request page — current state

Verified green on staging: 9/9 in ~50s, **and all nine pass individually** (5.5s-16.3s each).

- **Slot echo.** `expect_selected_slot_in_url(slot)` matches path + `shooting_date` +
  `shooting_time` (`{base}/photographers/<slug>/private_offers/new?shooting_date=2026-10-03&shooting_time=08:00`,
  no `$` anchor). `TC_01` calls it **before** `expect_available_slot()`, which asserts the rendered
  `2026/09/16` and the time **range** `08:00 - 09:00` (`SHOOTING_DURATION = 1h`) — asserting the end
  hour means a wrong-cell click cannot false-pass.
- **Payment table, no hardcoded money.** `read_option_cards()` reads label/price/state off the
  cards; `sum_subtotal()` adds every `tr` except `tr.total`;
  `expect_payment_table_matches_selection()` asserts one row per ticked option (label + price) and
  `合計 == sum_subtotal()`. `_price_cell(label)` matches on the `th` text only — the
  `tr.option_item` constraint is carried by the `option_rows` count assert beside it.
- **遠方出張料 (long-distance fee), gated on the form's warning.** `TC_05`: pick a genre →
  `select_filming_location()` (`"Tokyo Tower"`, first suggestion) → `has_long_distance_fee_warning()`
  → no warning ⇒ **skip** (a location that charges nothing is valid data) → the `遠方出張料` row
  exists and is > 0 → `expect_payment_table_matches_selection()` proves it is inside `合計`.
  Caveats: the probe has no explicit timeout, so a no-fee location costs 30s before the skip; the
  `longDistanceFee` warning has no saved fixture yet.

Open: submitting the form (`confirm_booking_button` is declared but unused, and
`//button[@type='submit']` is too broad — anchor it to `確認・決済に進む`), then the review/payment
page. No invalid-credentials test yet, though `LoginPage.expect_error` exists.
`TODO.md` is the live backlog — keep it in sync.

## Troubleshooting

- **`403 Forbidden` from `awselb/2.0`** — a User-Agent block, not an IP allowlist. Default `curl`
  gets 403; a Chrome UA gets 200.
- **Everything skipped** — `TEST_EMAIL`/`TEST_PASSWORD` empty in `.env`.
- **Timeout waiting for the login form** — stranded on Google SSO; re-run `scripts/save_auth.py`.
- **`Page.goto` times out on the very first test** — cold profile cache, Chrome is re-downloading
  `vendor.js`. Run `save_auth.py` once to warm the same profile.
- **Run 1 green, run 2 fails on `TC_01_login_form_is_displayed`** — the test lost its
  `logged_out` fixture argument, so the profile's `_session_id` survived from the previous run.
- **`launch_persistent_context` fails / profile locked** — close every Chrome window using
  `.auth/chrome-profile`.
- **`TC_05` reports `SKIPPED`** — no fee warning appeared. Either the spot genuinely charges no
  遠方出張料, or the `longDistanceFee` locator drifted. Always run with `-rs`: a silent skip keeps
  the suite green while asserting nothing.
- **`fixture '...' not found`, only at runtime** — run `scripts/check.py`; pyright cannot see
  fixture wiring, `--setup-plan` can.

## Working preferences

- Keep replies short and condensed.
- Repo prose (README, code comments) is in **Vietnamese** — match it when editing those files.
- Branch is `master`; upstream main branch is `main`.
