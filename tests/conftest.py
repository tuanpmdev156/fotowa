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

from pages.user.booking_request import BookingRequestPage
from pages.user.login import LoginPage
from pages.user.photographer_profile import BookingSlot, PhotographerProfilePage

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
    yield context
    context.close()


# Hai fixture này ghi đè `context`/`page` gốc của pytest-playwright, bỏ qua fixture `new_context` của plugin,
# nên --screenshot và --tracing trong pytest.ini không hoạt động.
@pytest.fixture(scope="session")
def context(browser_context: BrowserContext) -> BrowserContext:
    return browser_context


# Scope = function: mỗi test một tab mới, bắt đầu từ `about:blank` sạch.
# Đổi lại, mỗi test phải tự `goto_*` tới trang nó cần — không ăn ké trang test trước để lại.
@pytest.fixture
def page(context: BrowserContext) -> Iterator[Page]:
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture
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


def _sign_in(login_page: LoginPage, credentials: tuple[str, str]) -> None:
    """Đăng nhập app fotowa; đã đăng nhập rồi thì không làm lại.

    Là hàm thường chứ không phải fixture, để fixture ở scope nào cũng gọi được —
    cookie nằm ở `context` dùng chung nên đăng nhập trên tab nào thì mọi tab đều thấy.
    """
    login_page.goto_home_page()
    if login_page.is_logged_in():
        return

    login_page.goto_login_page()
    login_page.expect_login_form_loaded()
    login_page.login(*credentials)
    login_page.expect_logged_in()


@pytest.fixture
def logged_in(login_page: LoginPage, credentials: tuple[str, str]) -> None:
    """Đảm bảo đã đăng nhập app fotowa trước khi truy cập các trang khác."""
    _sign_in(login_page, credentials)


@pytest.fixture
def logged_out(context: BrowserContext) -> None:
    """Đảm bảo CHƯA đăng nhập — dành cho test form login.

    Profile giữ luôn cookie nên lần chạy sau sẽ vào thẳng trạng thái đã đăng nhập và test không
    thấy form. Chỉ xoá cookie session của app; cookie SSO (`AWSELBAuthSessionCookie-*`) phải giữ
    nguyên, xoá là kẹt lại ở Google.
    """
    context.clear_cookies(name=APP_SESSION_COOKIE)


@pytest.fixture(scope="session")
def photographer_path() -> str:
    """Path trang profile của photographer"""
    return f"/photographers/{PHOTOGRAPHER_NAME}"


# Phụ thuộc `logged_in` state: page object chỉ được tạo sau khi đăng nhập xong.
@pytest.fixture
def photographer_profile_page(
    page: Page, base_url: str, photographer_path: str, logged_in: None
) -> PhotographerProfilePage:
    return PhotographerProfilePage(page, base_url, photographer_path)


# Không cần `logged_in`: ta tới trang này bằng click từ calendar, luôn chạy sau khi đã đăng nhập.
@pytest.fixture
def booking_request_page(
    page: Page, base_url: str, photographer_path: str
) -> BookingRequestPage:
    return BookingRequestPage(page, base_url, photographer_path)


def _find_first_available_slot(profile: PhotographerProfilePage) -> BookingSlot:
    """Mở profile, tìm tuần có lịch trống, bấm ô trống đầu tiên. Trả về ngày/giờ của chính ô đó."""
    profile.goto_profile_page()
    profile.expect_calendar_loaded()
    profile.goto_week_with_available_date()
    return profile.select_first_available_slot()


@pytest.fixture(scope="session")
def available_slot(
    context: BrowserContext,
    base_url: str,
    photographer_path: str,
    credentials: tuple[str, str],
) -> BookingSlot:
    """Ngày/giờ của một slot còn trống — **chỉ là dữ liệu**, không để lại state trên tab nào.

    Tự mở một tab riêng, tìm xong thì đóng lại, nên không test nào ăn ké được vị trí browser.
    Test cần trang private offer thì tự gọi `goto_booking_request(available_slot)`.
    """
    scratch = context.new_page()
    try:
        _sign_in(LoginPage(scratch, base_url), credentials)
        return _find_first_available_slot(
            PhotographerProfilePage(scratch, base_url, photographer_path)
        )
    finally:
        scratch.close()


# Khác `available_slot` ở chỗ: fixture này đi **đường click thật** và để browser đứng lại ở trang
# đích. Chỉ dành cho test kiểm tra chính hành vi click (bấm ô → sang đúng URL).
@pytest.fixture
def selected_slot(photographer_profile_page: PhotographerProfilePage) -> BookingSlot:
    """Bấm slot trống đầu tiên trên calendar, trả về ngày/giờ của chính ô đó."""
    return _find_first_available_slot(photographer_profile_page)
