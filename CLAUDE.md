# fotowa-automation-project — context for Claude

End-to-end UI test suite for **fotowa** (staging), Playwright TypeScript + `@playwright/test`,
Page Object Model. README.md is in Vietnamese; the user is a QA/SDET on Windows 11 + PowerShell.

## Stack

Node 24 (`v24.15.0`), npm. `@playwright/test@1.63.0`, `typescript@7.0.2` (the Go compiler, not 5.x —
pin `typescript@5` if it ever misbehaves), `dotenv`, `tsx`, `@types/node`.
Browser: **installed Google Chrome** via `channel: 'chrome'`, `headless: false`.
**Do not run `npx playwright install`** — no bundled browser is used.

```powershell
npm test                                    # 9 tests, ~44s
npm run check                               # tsc --noEmit + playwright test --list, no browser
npx playwright test -g "TC_01_login_form_is_displayed"     # one test
npx playwright test --trace on              # tracing is CLI-only, see below
npm run report                              # open the HTML report
npm run auth                                # one-time manual Google SSO
```

`npm run check` is the static gate and the equivalent of the old `scripts/check.py`: `tsc --noEmit`
catches what pyright used to, and `playwright test --list` must print exactly **9 tests in 3 files**.
There is no linter — do not add one without being asked.

`playwright.config.ts` absorbs the old `pytest.ini`: `testDir: './e2e'`, `workers: 1`,
`fullyParallel: false`, `retries: 0`, `channel: 'chrome'`, `headless: false`,
`screenshot: { mode: 'only-on-failure', fullPage: true }`, `outputDir: './test-results'`,
`actionTimeout: 0` / `navigationTimeout: 0` (= keep Playwright's 30s defaults), `expect.timeout: 5s`.

**`workers: 1` is not tunable.** `launchPersistentContext` takes an exclusive lock on
`.auth/chrome-profile`, so a second worker cannot open it. It is also what makes worker-scoped
fixtures behave exactly like pytest's old session scope.

## Layout

```
src/config/env.ts                           the ONLY module that reads process.env
src/utils/format.ts                         pad2 / yen / plusOneHour / escapeRegExp
src/fixtures/test.ts                        fixtures + signIn() + requireCredentials()
src/pages/user/login.page.ts                LoginPage
src/pages/user/photographer-profile.page.ts PhotographerProfilePage + BookingSlot (calendar)
src/pages/user/booking-request.page.ts      BookingRequestPage + ShootingOption (private-offer form)
e2e/user-01-login.spec.ts                   2 tests
e2e/user-02-photographer-profile.spec.ts    2 tests
e2e/user-03-booking-request.spec.ts         5 tests (slot echo, payment table, long-distance fee)
scripts/save-auth.ts                        One-time manual Google SSO
dom-snapshots/user/booking/*.html           Saved DOM for writing XPath offline — numbers are stale
planS/typescript-migration.md               The Python → TypeScript port (done)
planS/booking-price-check.md                Write-up of the payment/fee verification work
planS/booking-confirm-payment.md            Plan for the review + payment page (blocked on its DOM)
.env.example                                Committed; `.env` and `.auth/` are gitignored
```

Spec files are `*.spec.ts` under `e2e/`; test titles keep the `TC_0N_...` ids as plain strings, so
pytest.ini's `python_functions = TC_* test_*` hack is gone.

## Auth model (the central constraint)

Two separate gates:

1. **Staging front door** — Google SSO (AWS Cognito → Google IdP), not automatable. Run `npm run auth`
   once; it signs in through a dedicated persistent Chrome profile (`.auth/chrome-profile`). It also
   writes `.auth/storage_state.json`, which **nothing reads** — the persistent profile already holds
   the SSO cookies; the file is only a manual escape hatch.
2. **App login** at `/users/sign_in` — a normal email/password form the tests drive. `signIn()`
   (a plain exported function, not a fixture, so any scope can call it): `gotoHomePage()` →
   short-circuit if `isLoggedIn()` → otherwise `gotoLoginPage()` → `login()` → `expectLoggedIn()`.
   The `loggedIn` fixture is a one-line wrapper. Cookies live on the shared `context`, so signing in
   on any tab logs in every tab — that is what keeps the per-test short-circuit cheap.

**Why a persistent profile instead of `newContext({ storageState })`:** `assets/bundle/vendor.js`
is 10.5 MB served uncompressed and blocks the parser. Cold cache ⇒ DOMContentLoaded ~110s ⇒ every
run failed on the first `goto`. Warm profile cache ⇒ 1.8s. (A separate profile, not the real one:
Chrome 136+ refuses remote debugging on the default user-data-dir.)

The profile keeps cookies too, so a run would otherwise start already logged in and
`TC_01_login_form_is_displayed` would find no form. The **`loggedOut` fixture** clears exactly one
cookie — `_session_id` (the Rails app session) — and the two login tests request it by name.
`AWSELBAuthSessionCookie-0`/`-1` is the SSO door and **must survive**; clearing all cookies strands
the run on Google.

Side effect: `launchPersistentContext` opens its own blank tab; the `page` fixture adds a fresh tab
per test. That blank tab is why a failure produces **two** PNGs (see below).

## Environment variables

Loaded from `.env` by `dotenv/config`, imported **first** in the only two entry points:
`playwright.config.ts` and `scripts/save-auth.ts`. Real shell vars win.

- `BASE_URL` — **required, no default**; missing ⇒ `env.baseUrl()` throws.
- `TEST_EMAIL` / `TEST_PASSWORD` — missing ⇒ `credentials()` returns `null` ⇒ the test skips.
- `PHOTOGRAPHER_NAME` (`bebe`) → `photographerPath()` → `/photographers/<slug>`, shared by both page
  objects. Currently commented out in `.env`, so it falls back to `bebe`.
- `AUTH_DIR` (`.auth`) and `AUTOMATION_PROFILE_DIR` (`.auth/chrome-profile`) — must resolve to the
  same profile for both the tests and `save-auth.ts`, or the run loses the warm cache and the SSO
  cookies.
- `AUTH_STATE`, `GOOGLE_SSO_LOGIN_TIMEOUT_MS` (300000) — only `save-auth.ts`.
- No timeout env var: Playwright defaults (30s action/navigation, 5s `expect`).

**`src/config/env.ts` is the only module allowed to touch `process.env`, and it exports functions,
not constants.** A top-level `const X = process.env.Y` in a page object would be read before dotenv
runs — the exact bug class the Python version had with `os.getenv` in a class body. Two rules encoded
there: empty string counts as unset (`??` alone would let `TEST_EMAIL=` through as a blank email),
and values are **not** trimmed (a password may legitimately end in a space).

## Fixtures (`src/fixtures/test.ts`)

**worker** (expensive, no per-test state): `persistentContext`, `appBaseUrl`, `appPhotographerPath`,
`workerCredentials`, `availableSlot`.
**test** (anything holding a `page`): `context` (override), `page` (override), `loginPage`,
`loggedIn`, `loggedOut`, `photographerProfilePage`, `bookingRequestPage`, `selectedSlot`.

```
context ──→ page ──→ loginPage ──→ loggedIn ──→ photographerProfilePage ──→ selectedSlot
   │          │                                 bookingRequestPage (no loggedIn dep)
   │          └──→ loggedOut  (login tests only)
   └──→ availableSlot   (opens and closes its own scratch tab; returns data only)
```

The scope rule is not a preference: a worker-scoped fixture cannot request a test-scoped one, so
`page → test` forces every page-object fixture to follow. Fixture names are `appBaseUrl` /
`appPhotographerPath` so they don't collide with Playwright's own `baseURL` or shadow the `env.*`
functions.

Overriding `context` injects the SSO-authenticated context; because fixtures are lazy, the built-in
`browser` / `browserName` fixtures are then never instantiated and no second Chrome launches.

**`availableSlot` vs `selectedSlot` — they look alike and are not.**
- `availableSlot` (worker) is **data**: it opens a scratch tab, signs in, walks the calendar, closes
  the tab, and returns a frozen `BookingSlot`. It leaves no browser state, so nothing can free-ride
  on it. Tests that need the private-offer page call `gotoBookingRequest(availableSlot)` — direct
  URL, no calendar walk.
- `selectedSlot` (test) goes through the **real click path** and leaves the browser on the
  destination page. Only `user-03::TC_01` uses it, because that test is the assertion *about* the
  click.

**The skip cascade does not exist in Playwright.** pytest's `credentials` fixture called
`pytest.skip()` and every downstream test skipped with it; here a worker fixture cannot skip at all,
and fixtures are resolved **before** the test body runs. So `workerCredentials` throws if unset, and
the guard is explicit: `requireCredentials()` (returns the credentials, skips if absent) is called
in the body of `user-01::TC_02`, and `skipWithoutCredentials()` runs in a `test.beforeEach` in
`user-02` and `user-03`. Calling it in `beforeEach` works because a fixture requested only by the
test function is not set up until after the hooks run. `TC_01_login_form_is_displayed` needs no
credentials and keeps running. The `list` reporter prints every skip with its reason, so there is no
`-rs` equivalent to remember.

## Artifacts

**Screenshots work through config alone — verified, no custom capture code.** Overriding
`context`/`page` does *not* bypass Playwright's own artifact capture the way it bypassed
pytest-playwright's, so the Python `_capture_screenshot` + `pytest_runtest_makereport` hook
(~30 LOC) has no counterpart here. Measured behaviour:

| `use.screenshot` | test fails | test passes |
|---|---|---|
| `only-on-failure` (default) | `test-results/<slug>/test-failed-{1,2}.png` | nothing |
| `off` | nothing | nothing |
| `on` | — | `test-finished-{1,2}.png` |

Two things to know: `fullPage: true` is set explicitly (Playwright's automatic screenshot is
viewport-only; the Python version used `full_page=True`), and every failure yields **two** PNGs
because Playwright shoots every open page and `launchPersistentContext` keeps its own blank tab.
PNGs are attached to the HTML report, alongside an `error-context.md` accessibility dump.

**There is no `--screenshot` CLI flag** in `@playwright/test` (unlike pytest-playwright) — the mode
is config-only, so changing it means editing `playwright.config.ts`.

**Tracing is now reachable but still not wired in.** `--trace on` works ad hoc from the CLI. Making
it per-test through config would need `startChunk`/`stopChunk` on the shared context, and
`availableSlot`'s scratch tab runs during the first test's fixture setup and would leak into that
test's chunk. Left out rather than made to lie.

## Conventions that bite if ignored

**Every test owns its tab and navigates itself.** `page` is test-scoped: each test starts at
`about:blank`, so the first line of a test is a `goto*`. Run order means nothing — the numbers in
`TC_01_` / `user-01-` are test-case ids, not a contract. Preconditions belong in fixtures, never in
"whatever the previous test left behind"; only **fixtures** form a dependency graph, tests do not.
Proving it is a separate act from a green suite: run every test on its own with `-g`.

**`await expect(...)` — the single biggest hazard.** A missing `await` makes the assertion never run
*and the test pass*. There are ~40 of them and `tsc` will not catch it. The guard is the
negative-direction check: break an assertion on purpose and confirm the test actually fails.

**Page objects: no actions in the constructor** — lazy locators only, or a fixture burns a 30s
timeout on `about:blank`. Naming: `goto*` navigates, `expect*` asserts, everything else acts.
`optionCard()` / `priceCell()` return a `Locator` and stay synchronous; everything else is `async`.

**Strict mode is on** and fotowa renders its header twice (desktop + mobile) — anchor to something
unique or add `.first()`.

**Locators are XPath + Japanese text** (`ログイン`, `遠方出張料`, `ログインに成功しました`) —
every locator, no CSS. Verified on Chrome: a chained `parent.locator("//x")` **is** scoped to the
parent, so the `//` prefix is safe. But `:visible` is a CSS-only pseudo-class and raises on an
XPath — use `.filter({ visible: true })` (see `genreOptions`). `hasText:` and `has:` work with XPath
unchanged.

**Login state is asserted positively, never by absence.** `loggedInMarker` is the ログアウト link
(`//a[@href='/users/sign_out' and @data-ga-label='sign-out']`); it matches 2 nodes and the desktop
one sits in a hover dropdown, so test for *attachment*, not visibility. `isLoggedIn()` is a cheap
`count() > 0` probe (not logged in is a normal outcome — must not burn 30s); `expectLoggedIn()`
retries; `expectLoginSuccess()` checks the one-shot `ログインに成功しました` notice and belongs to
the login test only.

**Anything Vue renders needs a retrying `expect()`.** `.all()`, `innerText()` and `count()` do not
auto-wait; reading a price table straight after a click returns the pre-update DOM.

**A bare `catch` swallows everything.** `hasLongDistanceFeeWarning()` must check
`error instanceof errors.TimeoutError` (import `errors` from `@playwright/test`) and rethrow the
rest, or a genuine bug gets reported as "no fee warning".

**`evaluateAll` has three type parameters, `<R, Arg, E>`** — not `<R, E>`. Writing
`evaluateAll<string[], HTMLElement>` silently puts `HTMLElement` in the `Arg` slot and leaves the
element type as the `HTMLElement | SVGElement` union, which then fails on `colSpan`/`innerText`.

**`tsx` is required for `scripts/save-auth.ts`.** Node 24's native type stripping removes types but
does not rewrite `import` into `require`, and the package is `"type": "commonjs"` — running
`node scripts/save-auth.ts` fails with `Cannot use import statement outside a module`.

## The booking calendar

Calendar `td`s carry **no date/time data** — an `available` cell holds only an icon. Everything is
derived from position: **hour** = row index into `table.time`; **day** = which `table.events` the
cell is in, indexed into `tr.dayname`; **year/month** = `tr.month` in `table.calendar__header`, but
a week straddling two months renders two `th[@colspan]`, so `readYearMonth(column)` walks the
colspans.

`gotoWeekWithAvailableDate()` clicks 次週 up to `MAX_WEEKS = 10` times — staging is often fully
booked, and that is data, not a bug. It uses `.count()` so a booked week costs one call, not a 30s
timeout. The gate after each click must be `page.waitForFunction` (cell exists **and** differs):
`not.toHaveText` passes the instant Vue detaches the `td` mid-rerender.

`selectFirstAvailableSlot()` pulls every cell's `className` in one `evaluateAll`, clicks the first
`available` one, returns a `BookingSlot`. Class membership is `css.split(/\s+/).includes('available')`
— **not** `css.includes('available')`, which also matches `unavailable`. Tests assert on the returned
value — no date is ever hardcoded.

## Booking request page — current state

Verified green on staging: 9/9 in ~44s, **and all nine pass individually** (5.1s–11.8s each).

- **Slot echo.** `expectSelectedSlotInUrl(slot)` matches path + `shooting_date` + `shooting_time`
  (`{base}/photographers/<slug>/private_offers/new?shooting_date=2026-10-03&shooting_time=08:00`,
  no `$` anchor). `TC_01` calls it **before** `expectAvailableSlot()`, which asserts the rendered
  `2026/09/16` and the time **range** `08:00 - 09:00` (`plusOneHour`) — asserting the end hour means
  a wrong-cell click cannot false-pass.
- **Payment table, no hardcoded money.** `readOptionCards()` reads label/price/state off the cards;
  `sumSubtotal()` adds every `tr` except `tr.total`; `expectPaymentTableMatchesSelection()` asserts
  one row per ticked option (label + price) and `合計 == sumSubtotal()`. `priceCell(label)` matches
  on the `th` text only — the `tr.option_item` constraint is carried by the `optionRows` count assert
  beside it. `yen()` pins the locale to `en-US`; letting `toLocaleString()` pick would render
  `¥24.200` on a `de-DE` machine and break every money assertion.
- **遠方出張料 (long-distance fee), gated on the form's warning.** `TC_05`: pick a genre →
  `selectFilmingLocation()` (`"Tokyo Tower"`, first suggestion) → `hasLongDistanceFeeWarning()` →
  no warning ⇒ **skip** (a location that charges nothing is valid data) → the `遠方出張料` row exists
  and is > 0 → `expectPaymentTableMatchesSelection()` proves it is inside `合計`. The probe now has
  an explicit 5s timeout, so a no-fee location costs 5s, not 30s. The `longDistanceFee` warning has
  no saved DOM snapshot yet.

Open: submitting the form (`confirmBookingButton` is declared but unused, and `//button[@type='submit']`
is too broad — anchor it to `確認・決済に進む`), then the review/payment page. No invalid-credentials
test yet. `TODO.md` is the live backlog — keep it in sync.

## Troubleshooting

- **`403 Forbidden` from `awselb/2.0`** — a User-Agent block, not an IP allowlist. Default `curl`
  gets 403; a Chrome UA gets 200.
- **Everything skipped** — `TEST_EMAIL`/`TEST_PASSWORD` empty in `.env`; the reason is printed.
- **Timeout waiting for the login form** — stranded on Google SSO; re-run `npm run auth`.
- **`page.goto` times out on the very first test** — cold profile cache, Chrome is re-downloading
  `vendor.js`. Run `npm run auth` once to warm the same profile.
- **Run 1 green, run 2 fails on `TC_01_login_form_is_displayed`** — the test lost its `loggedOut`
  fixture argument, so the profile's `_session_id` survived from the previous run.
- **`launchPersistentContext` fails / profile locked** — close every Chrome window using
  `.auth/chrome-profile`, and make sure no second `playwright test` is running (`workers: 1`).
- **`TC_05` reports skipped** — no fee warning appeared. Either the spot genuinely charges no
  遠方出張料, or the `longDistanceFee` locator drifted. A silent skip keeps the suite green while
  asserting nothing, so read the reason the reporter prints.
- **A test passes suspiciously fast** — look for a missing `await` in front of `expect`.

## Working preferences

- Keep replies short and condensed.
- Repo prose (README, code comments) is in **Vietnamese** — match it when editing those files.
- Single branch `master` — also the default branch on `origin`
  (https://github.com/tuanpmdev156/fotowa.git). There is no `main`; PRs target `master`.
