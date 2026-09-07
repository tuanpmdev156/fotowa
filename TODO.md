# TODO

Open items for the fotowa Playwright suite.

Status: the Windows venv works and pytest collects and runs 4 tests. They cannot pass yet -
staging returns `403 Forbidden` from this network, so there is no login form to interact with.

## Blocked on environment

- [x] ~~Recreate the virtualenv for Windows.~~ Done 2026-09-06: CPython 3.13.13 via
      `uv venv --python 3.13`, 18 packages from `requirements.txt`, Chromium 151.0.7922.34.
      Run with `.venv\Scripts\python.exe -m pytest` (or activate via
      `.venv\Scripts\Activate.ps1`).
      Note: this replaced a Linux venv, so any Docker/WSL workflow needs its own rebuild.
- [ ] **Get on an allowlisted network.** This is the only thing standing between the suite
      and a real run. `https://master.review.fotowa.com/users/sign_in` returns
      `403 Forbidden` from `awselb/2.0` with no `WWW-Authenticate` header - an IP allowlist,
      not basic auth. Verified from both curl and Chromium: page title is literally
      `403 Forbidden`. VPN or an allowlist entry for this machine.
- [ ] **Obtain staging credentials** and export them, or
      `test_valid_credentials_leave_login_page` stays skipped:
      ```powershell
      $env:TEST_EMAIL="..."; $env:TEST_PASSWORD="..."
      ```
- [ ] **Re-run once on an allowlisted network** and fix what falls over:
      `.venv\Scripts\python.exe -m pytest --headed --slowmo 500`

## `pages/login_page.py`

- [x] ~~Replace the English placeholder locators with the real Japanese ones.~~ Done - now
      `メールアドレス` / `パスワード` / `ログイン`.
- [ ] **Re-confirm the four locators against a page that actually loads.** They have still
      never matched a real element, because every run so far hit the 403 page. In particular
      `error_message` uses `get_by_text` with the full sentence, which breaks if the copy
      changes by a single character - consider anchoring on the alert container instead.
- [ ] Minor: `LoginPage.__init__` names its second parameter `base_url` and stores
      `self.base_url`, but `conftest.py` passes `login_url`. Positional so it works -
      rename for consistency.
- [ ] Watch for `.clear()` (or any other *action*) creeping back into `__init__`. Locators
      there must stay lazy declarations; an action runs at construction time, while the page
      is still `about:blank`, and every test errors out with a 30s timeout in the fixture.
      `fill()` already replaces existing content, so `clear()` is unnecessary anyway.

## `tests/test_login.py`

- [x] ~~Replace the `INVALID_CREDENTIALS_ERROR` placeholder.~~ Done - now
      `メールアドレスまたはパスワードが正しくありません`.
- [ ] **Replace the success assertion.** `test_valid_credentials_leave_login_page` only
      asserts `not_to_have_url(login_url)` because the post-login landing page is unknown.
      Assert on it properly once known.
- [ ] Consider a `HomePage`/`DashboardPage` page object for the post-login state, and have
      `LoginPage.login()` return it - the usual POM convention.
- [ ] Add cases once the basics pass: logged-out redirect, "remember me", password reset
      link, lockout after repeated failures.

## `tests/conftest.py`

The `browser_context` fixture has three open problems (its syntax errors are fixed, but the
design is unresolved):

- [ ] **It is never used.** `login_page` depends on pytest-playwright's `page` fixture, so
      the persistent Chrome context never launches. Wiring it in means overriding the
      `context`/`page` fixtures, not just defining a new one.
- [ ] **`user_data_dir` points at a profile subdirectory.** Chrome expects the *User Data*
      root plus `args=["--profile-directory=Profile 15"]`. As written it will create a fresh
      `Default` profile inside `Profile 15` instead of reusing that profile.
- [ ] **A persistent profile conflicts with testing login.** It carries existing session
      cookies, so the form may never appear. It also fails while Chrome is running, because
      the profile is locked. If the goal is to skip login for *other* tests, Playwright's
      `storage_state` is the better tool.
- [ ] Decide whether `login_url` should stay a full URL or go back to `base_url` + a path,
      so other page objects can share it.

## Housekeeping

- [ ] `tests/test_example.py` (the Playwright scaffold demo) was deleted - confirm that was
      intentional.
- [ ] Not a git repository yet. `git init` and add a `.gitignore` for `.venv/`,
      `__pycache__/`, `.pytest_cache/`, `test-results/`.
- [ ] Credentials are read from env vars - keep them out of the repo when CI is set up.
