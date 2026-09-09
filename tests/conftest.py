import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from playwright.sync_api import (
    BrowserContext,
    Page,
    Playwright,
    expect,
    sync_playwright,
)

from pages.booking_request import BookingRequestPage
from pages.login import LoginPage
from pages.photographer_profile import PhotographerProfilePage

ROOT = Path(__file__).resolve().parent.parent

# Thông tin đăng nhập và URL đích nằm trong `.env` (copy từ `.env.example`).
load_dotenv(ROOT / ".env")

# Test lấy trạng thái đăng nhập từ `storage_state`: chạy `scripts/save_auth.py` một lần để ghi ra `.auth/storage_state.json`, sau đó mọi test dùng lại cookie đó.

# Timeout mặc định cho mọi action/navigation/assertion, đặt một chỗ duy nhất ở fixture `page` bên dưới. 
DEFAULT_TIMEOUT_MS = int(os.getenv("DEFAULT_TIMEOUT_MS", 30000))

AUTH_DIR = Path(os.getenv("AUTH_DIR", ROOT / ".auth"))
AUTH_STATE = Path(os.getenv("AUTH_STATE", AUTH_DIR / "storage_state.json"))


@pytest.fixture(scope="session")
def base_url() -> str:
    # BASE_URL phải đến từ `.env` (hoặc từ biến môi trường của shell).
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


# Muốn browser dừng lại và KHÔNG đóng khi có lỗi: chạy `pytest --pdb`. pytest hoãn
# teardown của fixture cho tới lúc bạn thoát debugger, nên cửa sổ Chrome vẫn sống và
# giữ nguyên state ở thời điểm fail.
@pytest.fixture(scope="session")
def browser_context(playwright_instance: Playwright) -> Iterator[BrowserContext]:
    p = playwright_instance

    browser = p.chromium.launch(channel="chrome", headless=False)
    # Chưa có state đã lưu vẫn ổn với các test chỉ xem trang đăng nhập.
    state = str(AUTH_STATE) if AUTH_STATE.exists() else None
    context = browser.new_context(storage_state=state)
    yield context
    context.close()
    browser.close()


# Hai fixture này ghi đè `context`/`page` gốc của pytest-playwright, bỏ qua fixture `new_context` của plugin,
# nên --screenshot và --tracing trong pytest.ini không hoạt động.
@pytest.fixture(scope="session")
def context(browser_context: BrowserContext) -> BrowserContext:
    return browser_context


# Scope = session: dùng một tab cho các test cases
@pytest.fixture(scope="session")
def page(context: BrowserContext) -> Iterator[Page]:
    page = context.new_page()
    # Ba loại timeout riêng biệt: action, navigation, và assertion của `expect`
    # (mặc định chỉ 5s và không chịu ảnh hưởng của hai cái kia).
    page.set_default_timeout(DEFAULT_TIMEOUT_MS)
    page.set_default_navigation_timeout(DEFAULT_TIMEOUT_MS)
    expect.set_options(timeout=DEFAULT_TIMEOUT_MS)
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
    trước đã login rồi thì `is_logged_in()` ngắn mạch, không làm lại.
    """
    login_page.goto_home_page()
    if login_page.is_logged_in():
        return

    login_page.goto_login_page()
    login_page.expect_login_form_loaded()
    login_page.login(*credentials)
    assert login_page.is_logged_in(), "Failed to log in to the fotowa app"


# Phụ thuộc `logged_in` state: page object chỉ được tạo sau khi đăng nhập xong.
@pytest.fixture(scope="session")
def photographer_profile_page(
    page: Page, base_url: str, logged_in: None
) -> PhotographerProfilePage:
    return PhotographerProfilePage(page, base_url)


# Không cần `logged_in`: ta tới trang này bằng click từ calendar, nên nó luôn
# chạy sau test đã đăng nhập.
@pytest.fixture(scope="session")
def booking_request_page(page: Page, base_url: str) -> BookingRequestPage:
    return BookingRequestPage(page, base_url)


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
