# fotowa-automation-project — context for Claude

End-to-end UI test suite for **fotowa** (staging), Playwright Python + pytest, Page Object Model.
README.md is in Vietnamese; the user is a QA/SDET on Windows 11 + PowerShell.

## Stack

Python 3.13, venv at `.venv` (native Windows CPython — never reuse a Linux venv).
`pytest==8.3.4`, `pytest-playwright==0.6.2`, `python-dotenv==1.0.1`, `pyright==1.1.411`.
Browser: **installed Google Chrome** via `channel="chrome"`, `headless=False`. Env manager: `uv`.

```powershell
.venv\Scripts\python.exe -m pytest                       # 9 tests, ~20s
.venv\Scripts\python.exe -m pytest -rs                   # -rs: make skips visible
.venv\Scripts\python.exe -m pytest tests/test_user_01_login.py::TC_01_login_form_is_displayed
.venv\Scripts\python.exe scripts\check.py                # static gates, no browser
```

`pytest.ini`: `-v --browser chromium --screenshot only-on-failure --tracing retain-on-failure`,
`testpaths = tests`, `pythonpath = .`, `markers` (registers `incremental`), and
**`python_functions = TC_* test_*`** — tests are named by test-case id (`TC_01_...`); drop that
line and pytest collects nothing.

`scripts/check.py` = `pytest --setup-plan -q` (resolves every fixture without a browser — the only
way to catch a misspelled fixture name) + `pyright` (basic mode over `pages`, `tests`, `scripts`).
Run it before any browser run.

## Layout

```
pages/login.py                              LoginPage
pages/photographer_profile.py               PhotographerProfilePage + BookingSlot (calendar)
pages/booking_request.py                    BookingRequestPage + ShootingOption (private-offer form)
tests/conftest.py                           dotenv, session fixtures, `logged_in`, `selected_slot`
tests/test_user_01_login.py                 2 tests
tests/test_user_02_photographer_profile.py  2 tests
tests/test_user_03_booking_request.py       5 tests (slot echo, payment table, long-distance fee)
scripts/save_auth.py                        One-time manual Google SSO
scripts/check.py                            --setup-plan + pyright
fixtures/*.html                             Saved DOM for writing XPath offline — numbers are stale
plan/booking-price-check.md                 Write-up of the payment/fee verification work
plan/booking-confirm-payment.md             Plan for the review + payment page (blocked on its DOM)
.env.example                                Committed; `.env` and `.auth/` are gitignored
```

## Auth model (the central constraint)

Two separate gates:

1. **Staging front door** — Google SSO (AWS Cognito → Google IdP), not automatable. Run
   `scripts\save_auth.py` once; it signs in through a dedicated persistent Chrome profile
   (`.auth/chrome-profile`). It also writes `.auth/storage_state.json`, which **nothing reads** —
   `conftest.browser_context` uses `launch_persistent_context` on that same profile, so the SSO
   cookies are already in it.
2. **App login** at `/users/sign_in` — a normal email/password form the tests drive. The
   `logged_in` fixture runs once per session: `goto_home_page()` → short-circuit if
   `is_logged_in()` → otherwise `goto_login_page()` → `login()` → `expect_logged_in()`.

**Why a persistent profile instead of `new_context(storage_state=...)`:** `assets/bundle/vendor.js`
is 10.5 MB served uncompressed and blocks the parser. Cold cache ⇒ DOMContentLoaded ~110s ⇒ every
run failed on the first `goto`. Warm profile cache ⇒ 1.8s. (A separate profile, not the real one:
Chrome 136+ refuses remote debugging on the default user-data-dir.)

The profile keeps cookies too, so `browser_context` clears exactly one at session start:
`_session_id` (the Rails app session). Without it run 2 starts logged in and
`TC_01_login_form_is_displayed` finds no form. `AWSELBAuthSessionCookie-0`/`-1` is the SSO door and
**must survive** — clearing all cookies strands the run on Google.

Side effect: `launch_persistent_context` opens its own blank tab; the `page` fixture adds the tab
the tests actually use.

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

## Fixtures (all `scope="session"`, `tests/conftest.py`)

```
base_url → playwright_instance → browser_context → context → page
                                                               ↓
        login_page ──→ credentials ──→ logged_in ──→ photographer_profile_page
                                     photographer_path ──↗     │       booking_request_page
                                                               ↓       (no logged_in dep)
                                                          selected_slot
```

`booking_request_page` needs no `logged_in`: that page is reached by clicking a calendar slot.
`selected_slot` is the precondition for all of `test_user_03`: profile → calendar →
`goto_week_with_available_date` → `select_first_available_slot`, once per session, returning the
`BookingSlot` the tests assert against.

## Conventions that bite if ignored

**One tab, session fixtures, order is load-bearing.**
- Tests run in declaration order — hence `TC_01_` / `TC_02_` / … Each resumes where the previous
  one left the browser.
- Files are collected alphabetically, hence `test_user_01_` / `_02_` / `_03_`. A name that sorts
  before `test_user_01_login.py` pulls `logged_in` first and breaks the login test. Re-check with
  `pytest --collect-only -q` after any rename. (The `user` segment anticipates a split by role —
  see `TODO.md`.)
- A single test run alone starts at `about:blank`. Only **fixtures** form a dependency graph, not
  tests — move a precondition into a fixture to make a test standalone.

**`incremental` marker.** Two hooks in `conftest.py` keyed on `_failed_in_module`: after a marked
test fails, later tests in the same module skip with `test trước đó đã fail: <name>`. `Skipped` is
filtered out, so neither the `credentials` skip nor `TC_05`'s no-fee skip arms it.
`test_user_02` and `test_user_03` opt in via `pytestmark = pytest.mark.incremental`.

**Overridden `context`/`page`.** They inject the authenticated context and bypass the plugin's
`new_context`, so `--screenshot` / `--tracing` produce **no artifacts**. Accepted trade-off; use
`pytest --pdb` to inspect a failure live (teardown is deferred, the window stays open).

**Page objects: no actions in `__init__`** — lazy locators only, or a fixture burns a 30s timeout
on `about:blank`. Naming: `goto_*` navigates, `expect_*` asserts, everything else acts.

**Strict mode is on** and fotowa renders its header twice (desktop + mobile) — anchor to something
unique or add `.first`.

**Locators are XPath + Japanese text** (`ログイン`, `遠方出張料`, `ログインに成功しました`).

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

Verified green on staging (9/9, repeated runs):

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
page. `TC_05` also fails when run alone (`-k TC_05` times out in `select_first_genre()`) though it
passes with the file. No invalid-credentials test yet, though `LoginPage.expect_error` exists.
`TODO.md` is the live backlog — keep it in sync.

## Troubleshooting

- **`403 Forbidden` from `awselb/2.0`** — a User-Agent block, not an IP allowlist. Default `curl`
  gets 403; a Chrome UA gets 200.
- **Everything skipped** — `TEST_EMAIL`/`TEST_PASSWORD` empty in `.env`.
- **Timeout waiting for the login form** — stranded on Google SSO; re-run `scripts/save_auth.py`.
- **`Page.goto` times out on the very first test** — cold profile cache, Chrome is re-downloading
  `vendor.js`. Run `save_auth.py` once to warm the same profile.
- **Run 1 green, run 2 fails on `TC_01_login_form_is_displayed`** — the `_session_id` clear in
  `browser_context` was lost.
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
