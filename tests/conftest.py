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

# Test lấy trạng thái đăng nhập từ `storage_state`: chạy `scripts/save_auth.py` một
# lần để ghi ra `.auth/storage_state.json`, sau đó mọi test dùng lại cookie đó.
#
# Không dùng được `Profile 15` thật của bạn: Chrome 136+ từ chối remote debugging
# trên user-data-dir mặc định, còn App-Bound Encryption khiến cookie của một profile
# được copy sang chỗ khác không giải mã được. `scripts/save_auth.py` tồn tại để lấp
# khoảng trống đó bằng một lần đăng nhập tay.
AUTH_DIR = Path(os.getenv("AUTH_DIR", ROOT / ".auth"))
AUTH_STATE = Path(os.getenv("AUTH_STATE", AUTH_DIR / "storage_state.json"))


@pytest.fixture(scope="session")
def base_url():
    # Không có giá trị mặc định trong code: BASE_URL phải đến từ `.env` (hoặc từ
    # biến môi trường của shell). Thiếu thì fail ngay với thông báo rõ ràng, thay
    # vì âm thầm chạy test lên một site không ai ngờ tới.
    url = os.getenv("BASE_URL")
    if not url:
        pytest.fail(
            "Chưa có BASE_URL. Hãy copy `.env.example` thành `.env` rồi điền BASE_URL.",
            pytrace=False,
        )
    return url.rstrip("/")


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser_context(playwright_instance):
    p = playwright_instance

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
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session")
def login_page(page, base_url):
    return LoginPage(page, base_url)
