r"""Đăng nhập tay một lần, rồi lưu session vào .auth/storage_state.json.

    .venv\Scripts\python.exe scripts\save_auth.py

Script mở một cửa sổ Chrome với profile automation riêng (`.auth/chrome-profile`),
điều hướng tới BASE_URL và chờ bạn hoàn tất Google SSO. Ngay khi trình duyệt quay
về một trang fotowa, cookie sẽ được ghi vào `.auth/storage_state.json` và bộ test
tự động dùng lại.

Tại sao không dùng `Profile 15` thật của bạn? Chrome 136+ từ chối remote debugging
trên user-data-dir mặc định ("DevTools remote debugging requires a non-default data
directory"), còn App-Bound Encryption khiến cookie của một profile được copy sang
chỗ khác không giải mã được. Một thư mục riêng là con đường duy nhất Chrome cho
phép - và vì nó được giữ lại, lần SSO này thường chỉ mất công một lần.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

AUTH_DIR = Path(os.getenv("AUTH_DIR", ROOT / ".auth"))

AUTH_STATE = Path(os.getenv("AUTH_STATE", AUTH_DIR / "storage_state.json"))

PROFILE_DIR = Path(os.getenv("AUTOMATION_PROFILE_DIR", 
AUTH_DIR / "chrome-profile"))

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    sys.exit("Chưa có BASE_URL. Hãy copy `.env.example` thành `.env` rồi điền BASE_URL.")

BASE_URL = BASE_URL.rstrip("/")

# Thời gian giữ cửa sổ mở để bạn bấm qua các bước Google SSO.
LOGIN_TIMEOUT_MS = int(os.getenv("LOGIN_TIMEOUT_MS", 5 * 60 * 1000))

APP_HOST = urlsplit(BASE_URL).netloc


def logged_in(url: str) -> bool:
    """Trả về True khi đã quay lại đúng host của app.

    Khi chưa đăng nhập, BASE_URL trả 302 sang Cognito rồi sang Google, nên host
    lúc đó không phải APP_HOST. `/oauth2/...` bị loại trừ vì đó là bước trung
    gian của luồng SSO, cookie session chưa chắc đã được set xong.
    """
    parts = urlsplit(url)
    return parts.netloc == APP_HOST and not parts.path.startswith("/oauth2/")


def main() -> int:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(BASE_URL)

        if not logged_in(page.url):
            print(
                f"Sign in with your fotowa Google account in the Chrome window.\n"
                f"Waiting up to {LOGIN_TIMEOUT_MS // 1000}s for a redirect back to "
                f"{APP_HOST}...",
                flush=True,
            )
            try:
                page.wait_for_url(logged_in, timeout=LOGIN_TIMEOUT_MS)
            except Exception:
                print(f"\nNever reached a logged-in URL. Still at:\n  {page.url}",
                      file=sys.stderr)
                print("Nothing saved - re-run and finish the login.", file=sys.stderr)
                context.close()
                return 1

        final_url = page.url
        AUTH_STATE.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(AUTH_STATE))
        context.close()

    print(f"\nLogged in at {final_url}")
    print(f"Session saved -> {AUTH_STATE}")
    print("Tests now reuse it automatically; Chrome can stay open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
