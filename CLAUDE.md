# fotowa-automation-project — context for Claude

End-to-end UI test suite for **fotowa** (staging/review env), written in **Playwright Python +
pytest** using the Page Object Model. README.md is written in Vietnamese; the user is a QA/SDET
working from Windows 11 + PowerShell.

## Stack & runtime facts

| Thing | Value |
|---|---|
| Python | 3.13, venv at `.venv` (native Windows CPython — do **not** reuse a Linux venv here) |
| Deps | `pytest==8.3.4`, `pytest-playwright==0.6.2`, `python-dotenv==1.0.1` (`requirements.txt`) |
| Browser | **Installed Google Chrome**, via `channel="chrome"`, `headless=False`. Bundled Chromium is not used |
| Env manager | `uv` (`uv venv --python 3.13 --seed`, `uv pip install -r requirements.txt`) |

Run tests (PowerShell, from repo root):

```powershell
.venv\Scripts\python.exe -m pytest                      # no activation needed
.venv\Scripts\python.exe -m pytest --headed --slowmo 500
.venv\Scripts\python.exe -m pytest tests/test_login.py::test_login_form_is_displayed
```

`pytest.ini`: `-v --browser chromium --screenshot only-on-failure --tracing retain-on-failure`,
`testpaths = tests`, `pythonpath = .`.

## Layout

```
pages/login_page.py     Page object: locators (XPath) + page-level actions/assertions
tests/conftest.py       dotenv load, session-scoped playwright/browser_context/page/login_page
tests/test_login.py     2 active tests, 2 commented-out
scripts/save_auth.py    One-time manual Google SSO -> .auth/storage_state.json
.env.example            Committed template; .env and .auth/ are gitignored
```

## Auth model (the central constraint)

The staging site sits behind **Google SSO (AWS Cognito → Google IdP)** — there is no automatable
username/password form at the front door. So:

1. Run `.venv\Scripts\python.exe scripts\save_auth.py` once. It opens Chrome with a dedicated
   persistent profile (`.auth/chrome-profile`), waits (default 300s, `LOGIN_TIMEOUT_MS`) for a
   redirect back to `BASE_URL`'s host (excluding `/oauth2/*`), then dumps
   `.auth/storage_state.json`.
2. `conftest.browser_context` loads that `storage_state` if the file exists (absent is tolerated —
   tests that only view the login page still work).

Why a separate Chrome profile and not the user's real one: Chrome 136+ refuses remote debugging on
the default user-data-dir, and App-Bound Encryption makes copied cookies undecryptable.

## Environment variables

Loaded from `.env` via `load_dotenv` in both `conftest.py` and `save_auth.py`. Real shell env vars
win over the file.

- `BASE_URL` — **required, no code default**; missing ⇒ `pytest.fail` / `sys.exit`. Template value:
  `https://master.review.fotowa.com`.
- `TEST_EMAIL`, `TEST_PASSWORD` — tests needing an account are **skipped** if either is empty
  (`requires_account` marker in `tests/test_login.py`).
- `AUTH_DIR` (`.auth`), `AUTH_STATE` (`.auth/storage_state.json`),
  `AUTOMATION_PROFILE_DIR` (`.auth/chrome-profile`), `LOGIN_TIMEOUT_MS` (300000).

## Conventions that bite if ignored

**Session-scoped fixtures, shared tab.** `browser_context`, `page`, `login_page` are all
`scope="session"` — the whole run happens in **one tab**, and each test resumes wherever the
previous one left the browser. Consequences:
- Tests in a file run in **declaration order**, and order is load-bearing. Moving a test changes
  its starting state.
- Running one test alone (`-k valid_credentials`) starts at `about:blank`, so order-dependent tests
  fail in isolation. Add explicit navigation if a test must stand alone.
- `test_login_with_valid_credentials` deliberately reuses the form that
  `test_login_form_is_displayed` navigated to — it never calls `goto`.

**Overridden `context`/`page` fixtures.** `conftest.py` overrides pytest-playwright's own
`context`/`page` to inject the authenticated context. Side effect: the plugin's `new_context`
fixture is bypassed, so `--screenshot` and `--tracing` in `pytest.ini` currently **produce no
artifacts**. Known, accepted trade-off.

**Page objects: no actions in `__init__`.** Declare locators only (lazy `Locator` objects). The
fixture builds `LoginPage` while the page is still `about:blank`, so any `.click()/.fill()` there
would burn a 30s timeout inside the fixture. Method naming: `goto_*` navigate, `expect_*` assert,
everything else acts.

**Strict mode.** Playwright strict mode is on; fotowa renders its header **twice** (desktop +
mobile), so a naive selector hits 2 nodes and raises `strict mode violation`. Anchor to something
unique or add `.first`.

**Locators are XPath and Japanese-text-based** (`text()='ログイン'`, error text
`メールアドレスまたはパスワードが正しくありません`). The UI is Japanese.

## Troubleshooting (learned the hard way)

- **`403 Forbidden` from `awselb/2.0`** — a **User-Agent block**, not an IP allowlist, and no VPN is
  needed. Default `curl` gets 403; with a Chrome UA the site returns 200 and redirects to Google SSO.
- **Tests skipped "set TEST_EMAIL and TEST_PASSWORD"** — fill them in `.env`.
- **Timeout waiting for the login form** — you're probably stranded on the Google SSO page; the
  saved session expired. Re-run `scripts/save_auth.py`.
- **`launch_persistent_context` fails / profile locked** — close every Chrome window using
  `.auth/chrome-profile`.

## Current state / open items

- Only login is covered: `test_login_form_is_displayed` (active) and
  `test_login_with_valid_credentials` (active but has **no assertion yet** — TODO in the file:
  assert on the real post-login page once it's known).
- Two tests are commented out in `tests/test_login.py` and reference methods that **don't exist**
  on `LoginPage`: `goto()` and `submit()`. Reviving them needs those methods (or a rewrite to
  `goto_home_page`/`goto_login_page` + `login_button.click()`).
- `USE_CHROME_PROFILE` in `.env.example` is **dead** — no code reads it.
- README references a `TODO.md` that **does not exist** in the repo.
- README's closing "cleanup notes" section is **stale**: it claims `.gitignore` only has `.auth/`
  and `.env`, but `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `test-results/` are all
  ignored already (commit 92ee5fb).
- README's install step says `playwright install chromium`, but the suite actually runs on
  system Chrome (`channel="chrome"`).

## Working preferences

- Keep replies short and condensed.
- Repo prose (README, code comments) is in **Vietnamese** — match it when editing those files.
- Branch is `master`; upstream main branch is `main`.
