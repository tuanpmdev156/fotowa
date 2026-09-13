# Port fotowa-automation from Python/pytest to TypeScript/@playwright/test

## Context

The suite is a 9-test Playwright UI suite against fotowa staging, written in Python + pytest with a
Page Object Model. It works (9/9 green, ~50s, each test also passes individually), but a meaningful
slice of it exists only to work around pytest-playwright: a `pytest_runtest_makereport` hook plus a
21-line `_capture_screenshot` replace artifact capture the plugin skips once `context`/`page` are
overridden, and `scripts/check.py` exists because pytest resolves fixtures by string name at
runtime, so only `--setup-plan` catches a typo'd fixture name.

`@playwright/test` is Playwright's first-party runner: typed fixtures (a misspelled fixture becomes
a compile error), artifact capture as config, and the identical locator API — all ~45 XPath
locators port verbatim, Japanese text and `has:`/`hasText:` included.

**Decisions already taken:** port alongside Python and delete Python in a follow-up commit;
`@playwright/test`; npm; keep `chromium.launchPersistentContext()` on the same `.auth/chrome-profile`;
port `save_auth.py`, drop `check.py`; page objects keep taking `baseUrl` (1:1 port, not Playwright's
`baseURL`); comments stay Vietnamese; `fixtures/` → `dom-snapshots/`.

**Non-goals:** no new test cases, no behaviour changes, no CI, no headless mode. Success = the TS
suite reproduces the same 9 assertions, passes 9/9 as a suite, and passes 9/9 individually.

---

## Step 0 — Prerequisite: install Node (blocking, user action)

`node`, `npm`, and `node_modules` do not exist on this machine — verified: `node --version` →
not found, and nothing under `Program Files\nodejs`, `AppData\Roaming\npm`, fnm or Volta.

Install Node 22 LTS (winget: `winget install OpenJS.NodeJS.LTS`), reopen the shell, confirm
`node -v` and `npm -v`. Nothing below can run until this is done.

---

## Scope

| Python | → TypeScript |
|---|---|
| `pages/user/login.py` (67) | `src/pages/user/login.page.ts` |
| `pages/user/photographer_profile.py` (130) | `src/pages/user/photographer-profile.page.ts` |
| `pages/user/booking_request.py` (216) | `src/pages/user/booking-request.page.ts` |
| `tests/conftest.py` (276) | `src/fixtures/test.ts` + `src/config/env.ts` + `playwright.config.ts` |
| `tests/test_user_0{1,2,3}_*.py` (98) | `e2e/user-0{1,2,3}-*.spec.ts` |
| `scripts/save_auth.py` (94) | `scripts/save-auth.ts` |
| `scripts/check.py` (46) | *deleted* — `npm run check` = `tsc --noEmit` + `playwright test --list` |
| `pytest.ini`, `pyrightconfig.json`, `requirements.txt` | `playwright.config.ts`, `tsconfig.json`, `package.json` |
| `fixtures/user/booking/*.html` | `git mv` → `dom-snapshots/user/booking/` (no code reads these) |

Reused unchanged: `.env` / `.env.example` (same variables), `.auth/chrome-profile` (same warm
profile, already holds the SSO cookies), `plan/*.md`.

New dirs (`src/`, `e2e/`) do not collide with Python's `pages/`, `tests/` — both suites coexist
until the deletion commit.

---

## Step 1 — Project scaffold

`npm init -y`, then `npm i -D @playwright/test typescript dotenv @types/node`. **Do not** run
`npx playwright install` — the suite uses installed Google Chrome via `channel: 'chrome'`.

**`tsconfig.json`** — `strict: true`, `target`/`lib` ES2022, `module: nodenext`, `noEmit: true`,
include `src`, `e2e`, `scripts`, `playwright.config.ts`. Strict mode is the point of the port; do
not relax it to make the port compile.

**`playwright.config.ts`** — absorbs `pytest.ini` and the parts of `conftest.py` that are config:

```ts
import 'dotenv/config';               // MUST be the first import — see Step 2
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  workers: 1,                         // mandatory, see below
  fullyParallel: false,
  reporter: [['list'], ['html', { open: 'never' }]],
  outputDir: './test-results',
  use: {
    channel: 'chrome',
    headless: false,
    screenshot: 'only-on-failure',
    actionTimeout: 0,                 // keep Playwright's 30s/5s defaults
  },
});
```

`workers: 1` is **not tunable**: `launchPersistentContext` takes an exclusive lock on the profile
directory, so a second worker cannot open it. That is also what makes worker-scoped fixtures behave
exactly like pytest's session scope. Leave a comment saying so — a future reader will try to raise it.

**`package.json` scripts** (replacing the pytest recipes in README):

| npm script | replaces |
|---|---|
| `test` | `pytest` |
| `test:headed` → `playwright test --headed` | `pytest --headed --slowmo 500` |
| `test -- -g "TC_01_login_form_is_displayed"` | single nodeid |
| `check` → `tsc --noEmit && playwright test --list` | `scripts/check.py` |
| `auth` → `tsx scripts/save-auth.ts` (or `node --experimental-strip-types`) | `scripts/save_auth.py` |

`pytest -rs` has no equivalent — the `list` reporter already prints every skip with its reason, so
the "silent skip" trap in `TC_05` is visible by default. Note that in `CLAUDE.md`.

---

## Step 2 — `src/config/env.ts`: kill the dotenv load-order trap structurally

`CLAUDE.md` documents a real bug class: `conftest` imports `pages.*` before `load_dotenv()`, so an
`os.getenv` in a page-object class body silently takes the default. TypeScript has the identical
hazard with top-level `const X = process.env.Y`.

Forbid it structurally: **`src/config/env.ts` is the only module allowed to touch `process.env`**,
and it exposes *functions*, not constants:

```ts
export function baseUrl(): string        // throws if unset — replaces pytest.fail(pytrace=False)
export function credentials(): Credentials | null   // null when EITHER is empty
export function photographerPath(): string          // `/photographers/${PHOTOGRAPHER_NAME ?? 'bebe'}`
export function profileDir(): string                // AUTOMATION_PROFILE_DIR ?? .auth/chrome-profile
```

Two traps to encode here:

- **Empty string ≠ unset.** Python's `if not (email and password)` catches both; `??` catches only
  `undefined`. Use `||` or an explicit `!== ''` check, or `TEST_EMAIL=` in `.env` silently passes a
  blank email to the login form.
- `import 'dotenv/config'` goes at the top of `playwright.config.ts` **and** `scripts/save-auth.ts`
  (the two entry points). No page object or fixture imports dotenv.

Also add `src/utils/format.ts` for the four things Python got from stdlib:
`pad2(n)` (`String(n).padStart(2,'0')`), `yen(n)` (**`n.toLocaleString('en-US')` — pin the locale
explicitly**, or a `de-DE` runner renders `¥24.200` and every money assertion breaks),
`plusOneHour('08:00')` (hand-rolled ~4 lines, no date library), and `escapeRegExp(s)` (Node has no
`RegExp.escape`).

---

## Step 3 — `src/fixtures/test.ts`: the conftest equivalent

```ts
type WorkerFixtures = {
  persistentContext: BrowserContext;
  workerCredentials: Credentials;
  availableSlot: BookingSlot;
};
type TestFixtures = {
  loginPage: LoginPage;
  loggedIn: void;
  loggedOut: void;
  photographerProfilePage: PhotographerProfilePage;
  bookingRequestPage: BookingRequestPage;
  selectedSlot: BookingSlot;
};
export const test = base.extend<TestFixtures, WorkerFixtures>({ ... });
```

Mapping, one line each:

- `persistentContext` (worker) — `mkdirSync(profileDir(), {recursive:true})` then
  `chromium.launchPersistentContext(profileDir(), { channel: 'chrome', headless: false })`;
  close on teardown. Replaces `playwright_instance` + `browser_context` (Playwright Test owns the
  driver lifecycle, so there is no `sync_playwright()` fixture to port).
- **`context` (override)** — `async ({ persistentContext }, use) => use(persistentContext)`.
  Overriding `context` means the built-in `browser` / `browserName` fixtures are never instantiated
  (fixtures are lazy), so no second Chrome launches.
- **`page` (override)** — `context.newPage()` → `use(page)` → capture screenshot → `page.close()`.
  Same "every test owns its tab, so line 1 of every test is a `goto_*`" contract.
- `loggedOut` — `context.clearCookies({ name: '_session_id' })`. **Only that cookie.** Clearing
  `AWSELBAuthSessionCookie-0/-1` strands the run on Google. Keep the comment.
- `loggedIn` — wraps a plain exported `signIn(loginPage, creds)` function (not a fixture), exactly
  as Python does, so any scope can call it.
- `availableSlot` (worker) — opens its own scratch tab, signs in, walks the calendar, closes the
  tab, returns frozen data. Depends on `persistentContext` + `workerCredentials`, never on `page`.
- `selectedSlot` (test) — the real click path, leaves the browser on the destination page. One test.

Keep the Vietnamese dependency-graph docstring from `conftest.py` at the top of this file.

### The screenshot question — verify before writing much

Playwright's built-in `screenshot: 'only-on-failure'` is wired through its own `_contextFactory`.
**It is likely that overriding `context` bypasses it, exactly as it did in Python** — but this
depends on Playwright internals I could not verify (no `node_modules` on this machine yet, and it
has changed across versions). So: after Step 1 installs the package, write one deliberately failing
test and check whether a PNG lands in `test-results/`.

- **If capture fires:** delete `_capture_screenshot` entirely and let config do it. ~30 LOC gone.
- **If it does not:** port it, but ~8 lines instead of 21 — `testInfo.status !== testInfo.expectedStatus`
  replaces the whole `pytest_runtest_makereport` + `StashKey` hook, and `testInfo.attach()` puts the
  PNG in the HTML report instead of a bare directory. Honour `testInfo.project.use.screenshot`
  (note it may be `'only-on-failure'` or `{ mode: ... }`), wrap the `page.screenshot()` in
  `try/catch` so a crashed tab can't mask the real failure.

Per-test `tracing.startChunk()/stopChunk()` is now *reachable* but is **deferred, not in scope** —
`availableSlot`'s scratch tab runs during the first test's fixture setup and would leak into that
test's chunk. `--trace on` ad hoc is enough for now. Record this in `CLAUDE.md` so the existing
"trace is impractical" note is updated rather than left stale.

### The skip cascade

Python's `credentials` fixture calls `pytest.skip()` and every downstream test skips invisibly.
Playwright has no fixture-level skip cascade, and a worker fixture cannot skip at all. Use an
explicit guard, which is also more honest:

```ts
// src/fixtures/test.ts
export function skipWithoutCredentials() {
  test.skip(credentials() === null, 'Must set TEST_EMAIL and TEST_PASSWORD in `.env`');
}
```

Call it in a `test.beforeEach` in `user-02` and `user-03`, and inside `TC_02` of `user-01`.
`TC_01_login_form_is_displayed` needs no credentials and keeps running — matching Python, where it
depends only on `login_page` + `logged_out`. `workerCredentials` then just throws if unset; no test
that needs it can reach it un-skipped.

---

## Step 4 — Port the three page objects

Mechanical, but four things to get right. All ~45 XPath locators copy across **unchanged**,
including chained `.locator("//x")` scoping and `has:`/`hasText:`.

1. **Constructors stay synchronous** — locators are lazy. The existing "no actions in `__init__`"
   rule maps perfectly onto TS classes; keep it.
2. **Every method becomes `async`.** `_option_card()` and `_price_cell()` are the exceptions —
   they return a `Locator` and stay sync.
3. **`await expect(...)` — the single biggest hazard.** A missing `await` on `expect` makes the
   assertion never run *and the test pass*. There are ~40 of them. `tsc --noEmit` will not catch it;
   add `@typescript-eslint/no-floating-promises` if you want it caught, otherwise the guard is the
   negative-direction check in Step 6.
4. `.filter(visible=True)` → `.filter({ visible: true })`; `css.split()` membership →
   `css.split(/\s+/).includes('available')` — **not** `css.includes('available')`, which also
   matches `unavailable`.

`BookingSlot` and `ShootingOption` (frozen dataclasses) → `interface` with `readonly` fields.
`raise AssertionError(msg)` → `throw new Error(msg)`; bare `assert` → `expect(...).toEqual([])` /
`.toBeGreaterThan(0)`.

**Two fixes to fold in while porting** (both already known, neither is scope creep):
- `has_long_distance_fee_warning()` calls `waitFor({state:'visible'})` with no timeout, so a no-fee
  location burns the full 30s before skipping. Pass `{ timeout: 5_000 }` as the original plan
  specified.
- `PlaywrightTimeoutError` → in TS, a bare `catch` swallows *every* error. Check
  `e instanceof errors.TimeoutError` (import `errors` from `@playwright/test`) or a genuine bug
  will be reported as "no fee warning".

Optional: fix the `current_year_moth` → `currentYearMonth` typo.

---

## Step 5 — Port the 9 tests

`e2e/user-01-login.spec.ts` (2), `user-02-photographer-profile.spec.ts` (2),
`user-03-booking-request.spec.ts` (5). Keep the `TC_0N_...` names verbatim as the test title string
— `pytest.ini`'s `python_functions = TC_* test_*` hack disappears entirely, since Playwright test
names are just strings. Keep the Vietnamese comments explaining why `TC_01` uses `selectedSlot`
rather than `goto_booking_request`, and why the URL assert comes first.

No `parametrize`, `monkeypatch`, or markers exist anywhere in the suite, so there is nothing else to
translate. `TC_03`/`TC_04` iterate options in the test body and port as-is.

---

## Step 6 — Verify

```powershell
npm run check                       # tsc --noEmit + playwright test --list → must list exactly 9
npm test                            # expect 9/9 (or 8 passed + TC_05 skipped, printed with reason)
```

Then the checks that actually prove the port, in order:

1. **Independence** — run all 9 nodeids individually (`npx playwright test -g "TC_01_..."`, etc.).
   This is the property the Python suite worked hardest for; a green suite does not prove it.
2. **Negative direction** — the guard against a missing `await expect`. Temporarily break one
   assertion in each page object (e.g. assert the wrong total, point `_priceCell` at a bogus label)
   and confirm the test actually **fails**. An assertion that never ran looks identical to a passing
   one.
3. **Screenshot behaviour** — force a failure, confirm a full-page PNG appears (Step 3's open
   question), and that `--screenshot off` / `on` still behave like the Python `--screenshot` modes.
4. **Cross-check against Python** — run `.venv\Scripts\python.exe -m pytest -rs` and the TS suite
   back to back; same pass/skip pattern, comparable timings (~50s suite, 5.5–16.3s per test).
   Do this **before** deleting anything.
5. **Cold-profile sanity** — close every Chrome window on `.auth/chrome-profile` first, or
   `launchPersistentContext` fails on the directory lock.

---

## Step 7 — Delete Python (separate commit, only after Step 6 passes)

`pages/`, `tests/`, `scripts/check.py`, `scripts/save_auth.py`, `pytest.ini`, `pyrightconfig.json`,
`requirements.txt`, `.venv/`, `.pytest_cache/`, `.vscode/settings.json` (entirely Python-oriented).
Update `.gitignore`: drop `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.venv/`; add `node_modules/`.

Then rewrite the docs, which are the real deliverable alongside the code:

- **`CLAUDE.md`** — stack, commands, layout, fixture table and scope rule (session→worker,
  function→test), the `workers: 1` reason, the screenshot outcome from Step 3, the updated tracing
  note. **Drop the two stale claims**: it references `plan/independent-tests.md` (deleted) and
  `LoginPage.expect_error` (never existed).
- **`README.md`** (Vietnamese) — swap the uv/venv install for Node/npm, the pytest recipes for the
  npm scripts, keep the `PHOTOGRAPHER_NAME` guidance. Note `PHOTOGRAPHER_NAME` is currently
  commented out in `.env`, so it falls back to `bebe`.
- **`TODO.md`** — the three open items (submit the booking form; the review/payment page; split by
  role) all survive the port unchanged. The "Lưu ý khi viết test" conventions block needs its
  pytest specifics rewritten. Add per-test tracing as a new item.
- **`.env.example`** — while here, delete the dead `USE_CHROME_PROFILE` (no code reads it) and
  document `AUTH_DIR` / `AUTOMATION_PROFILE_DIR` / `AUTH_STATE`, which are read but undocumented.

Note for Step 7: `scripts/save-auth.ts` writes `.auth/storage_state.json`, which **nothing reads** —
the persistent profile carries the cookies. Either drop that write during the port or keep it and
label it explicitly as a manual escape hatch.
