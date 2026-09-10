import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from playwright.sync_api import (
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

from pages.booking_request import BookingRequestPage
from pages.login import LoginPage
from pages.photographer_profile import PhotographerProfilePage

ROOT = Path(__file__).resolve().parent.parent

# Thông tin đăng nhập và URL đích nằm trong `.env` (copy từ `.env.example`).
load_dotenv(ROOT / ".env")

# Cổng SSO của staging: chạy `scripts/save_auth.py` một lần để đăng nhập Google vào profile
# `.auth/chrome-profile`; test dùng lại chính profile đó (xem fixture `browser_context`).

# Photographer dùng cho test calendar/booking. Default là photographer "bebe"
PHOTOGRAPHER_NAME = os.getenv("PHOTOGRAPHER_NAME", "bebe")

AUTH_DIR = Path(os.getenv("AUTH_DIR", ROOT / ".auth"))

# Profile Chrome dùng chung với `scripts/save_auth.py`: giữ cookie SSO **và** disk cache.
AUTOMATION_PROFILE_DIR = Path(
    os.getenv("AUTOMATION_PROFILE_DIR", AUTH_DIR / "chrome-profile")
)

# Cookie session của app fotowa (Rails), khác với cookie cổng SSO `AWSELBAuthSessionCookie-*`.
APP_SESSION_COOKIE = "_session_id"


@pytest.fixture(scope="session")
def base_url() -> str:
    url = os.getenv("BASE_URL")
    if not url:
        pytest.fail(
            "BASE_URL is not set. Copy `.env.example` to `.env` and fill in BASE_URL.",
            pytrace=False,
        )
    return url.rstrip("/")


@pytest.fixture(scope="session")
def playwright_instance() -> Iterator[Playwright]:
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser_context(playwright_instance: Playwright) -> Iterator[BrowserContext]:
    p = playwright_instance

    # Mở lại profile cũ, không tạo context mới, để giữ cache của Chrome.
    # `vendor.js` nặng 10.5 MB và không nén: cache rỗng mất 110s, quá 30s timeout của goto.
    # Có cache thì 1.8s. Cookie SSO cũng nằm sẵn trong profile.
    # Lưu ý: đóng hết cửa sổ Chrome đang mở profile này, không thì bị khoá.
    AUTOMATION_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(AUTOMATION_PROFILE_DIR),
        channel="chrome",
        headless=False,
    )
    # Profile giữ luôn cookie, nên lần chạy sau sẽ vào thẳng trạng thái đã đăng nhập và
    # `test_01_login_form_is_displayed` không thấy form. Xoá cookie login của app để mỗi lần
    # chạy đều bắt đầu từ chưa đăng nhập. Cookie SSO (`AWSELBAuthSessionCookie-*`) giữ nguyên,
    # xoá là kẹt lại ở Google.
    context.clear_cookies(name=APP_SESSION_COOKIE)

    yield context
    context.close()


# Hai fixture này ghi đè `context`/`page` gốc của pytest-playwright, bỏ qua fixture `new_context` của plugin,
# nên --screenshot và --tracing trong pytest.ini không hoạt động.
@pytest.fixture(scope="session")
def context(browser_context: BrowserContext) -> BrowserContext:
    return browser_context


# Scope = session: dùng một tab cho các test cases
@pytest.fixture(scope="session")
def page(context: BrowserContext) -> Iterator[Page]:
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session")
def login_page(page: Page, base_url: str) -> LoginPage:
    return LoginPage(page, base_url)


@pytest.fixture(scope="session")
def credentials() -> tuple[str, str]:
    """Tài khoản user fotowa."""
    email = os.getenv("TEST_EMAIL")
    password = os.getenv("TEST_PASSWORD")
    if not (email and password):
        pytest.skip("Must set TEST_EMAIL and TEST_PASSWORD in `.env`")
    return email, password


@pytest.fixture(scope="session")
def logged_in(login_page: LoginPage, credentials: tuple[str, str]) -> None:
    """Đảm bảo đã đăng nhập app fotowa trước khi truy cập các trang khác.

    Fixture này đăng nhập qua form một lần cho cả session. Nếu test đăng nhập chạy
    trước đã login rồi thì không làm lại.

    """
    login_page.goto_home_page()
    if login_page.is_logged_in():
        return

    login_page.goto_login_page()
    login_page.expect_login_form_loaded()
    login_page.login(*credentials)
    login_page.expect_logged_in()


@pytest.fixture(scope="session")
def photographer_path() -> str:
    """Path trang profile của photographer"""
    return f"/photographers/{PHOTOGRAPHER_NAME}"


# Phụ thuộc `logged_in` state: page object chỉ được tạo sau khi đăng nhập xong.
@pytest.fixture(scope="session")
def photographer_profile_page(
    page: Page, base_url: str, photographer_path: str, logged_in: None
) -> PhotographerProfilePage:
    return PhotographerProfilePage(page, base_url, photographer_path)


# Không cần `logged_in`: ta tới trang này bằng click từ calendar, luôn chạy sau khi đã đăng nhập.
@pytest.fixture(scope="session")
def booking_request_page(
    page: Page, base_url: str, photographer_path: str
) -> BookingRequestPage:
    return BookingRequestPage(page, base_url, photographer_path)


# --- Test chạy nối tiếp trên cùng một tab: test sau bị skip nếu test trước fail ---
# Đánh dấu bằng `pytestmark = pytest.mark.incremental` ở đầu file test.
_failed_in_module: dict[str, str] = {}


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> None:
    if "incremental" not in item.keywords:
        return
    if call.excinfo is not None and call.excinfo.typename != "Skipped":
        _failed_in_module.setdefault(item.module.__name__, item.name)  # type: ignore[attr-defined]


def pytest_runtest_setup(item: pytest.Item) -> None:
    if "incremental" not in item.keywords:
        return
    failed = _failed_in_module.get(item.module.__name__)  # type: ignore[attr-defined]
    if failed is not None:
        pytest.skip(f"test trước đó đã fail: {failed}")
