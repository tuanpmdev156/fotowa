import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from pages.login_page import LoginPage

ROOT = Path(__file__).resolve().parent.parent

# Thông tin đăng nhập và URL đích nằm trong `.env` (copy từ `.env.example`). Load ở
# đây vì conftest được import trước các module test, mà các module đó đọc biến môi
# trường ngay lúc import. Biến môi trường thật luôn được ưu tiên hơn file.
load_dotenv(ROOT / ".env")

# Có hai cách để có một trình duyệt đã đăng nhập:
#
#   1. storage_state (mặc định). Chạy `scripts/save_auth.py` một lần để ghi ra
#      `.auth/storage_state.json`, sau đó mọi test dùng lại cookie đó.
#   2. Profile automation cố định, bật bằng USE_CHROME_PROFILE=1. Dùng lại
#      `.auth/chrome-profile`, profile này giữ trạng thái đăng nhập qua các lần chạy.
#
# Cả hai cách đều không thể dùng `Profile 15` thật của bạn: Chrome 136+ từ chối
# remote debugging trên user-data-dir mặc định, còn App-Bound Encryption khiến
# cookie của một profile được copy sang chỗ khác không giải mã được.
# `scripts/save_auth.py` tồn tại để lấp khoảng trống đó bằng một lần đăng nhập tay.
USE_CHROME_PROFILE = os.getenv("USE_CHROME_PROFILE") == "1"
AUTH_DIR = Path(os.getenv("AUTH_DIR", ROOT / ".auth"))
AUTH_STATE = Path(os.getenv("AUTH_STATE", AUTH_DIR / "storage_state.json"))
PROFILE_DIR = Path(os.getenv("AUTOMATION_PROFILE_DIR", AUTH_DIR / "chrome-profile"))


@pytest.fixture(scope="session")
def base_url():
    return os.getenv("BASE_URL", "https://master.review.fotowa.com")


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser_context(playwright_instance):
    p = playwright_instance

    if USE_CHROME_PROFILE:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
        )
        yield context
        context.close()
        return

    browser = p.chromium.launch(channel="chrome", headless=False)
    # Chưa có state đã lưu vẫn ổn với các test chỉ xem trang đăng nhập.
    state = str(AUTH_STATE) if AUTH_STATE.exists() else None
    context = browser.new_context(storage_state=state)
    yield context
    context.close()
    browser.close()


# Hai fixture này ghi đè `context`/`page` gốc của pytest-playwright để test chạy
# trong context đã đăng nhập ở trên. Tác dụng phụ: nó bỏ qua fixture `new_context`
# của plugin, nên --screenshot và --tracing trong pytest.ini không còn tạo ra gì.
@pytest.fixture(scope="session")
def context(browser_context):
    return browser_context


# Cố ý dùng scope session: chỉ một tab cho cả lần chạy, để mỗi test tiếp tục từ nơi
# test trước để lại trình duyệt thay vì tải lại từ đầu.
# Đánh đổi là các test trong cùng file phụ thuộc thứ tự và dùng chung trạng thái -
# nếu một test đầu để trang ở chỗ không mong đợi, các test sau sẽ thừa hưởng nó.
@pytest.fixture(scope="session")
def page(context):
    # Context cố định đã có sẵn một trang trắng đang mở; dùng lại trang đó thay vì
    # để lại một tab bỏ không.
    page = context.pages[0] if context.pages else context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session")
def login_page(page, base_url):
    return LoginPage(page, base_url)
