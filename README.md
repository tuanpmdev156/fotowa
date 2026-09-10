# Dự án Automation fotowa

Bộ test UI end-to-end cho dự án Fotowa, viết bằng
[Playwright](https://playwright.dev/python/) và pytest theo mô hình POM (Page Object Model).

---

## Cấu hình

| Công cụ | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.13 | `.venv` trong repo là CPython bản native cho Windows |
| [uv](https://docs.astral.sh/uv/) | 0.11+ | Tạo venv và cài package (nhanh hơn `pip`, tự tải đúng bản Python) |
| Playwright | 1.62.0 | Cài kèm `pytest-playwright==0.6.2` trong `requirements.txt` |
| Google Chrome | đã cài sẵn trong máy | Test chạy bằng `channel="chrome"`, **không** dùng Chromium đi kèm Playwright |

Cần một tài khoản Google fotowa có quyền truy cập trang staging để làm được bất cứ việc gì sau
trang đăng nhập.

### Biến môi trường

Copy `.env.example` thành `.env` rồi điền giá trị của bạn. `.env` đã được gitignore — tuyệt đối
không commit file này.

Bắt buộc phải điền `BASE_URL`, `TEST_EMAIL`, `TEST_PASSWORD`. Các biến còn lại đều có default
trong code, thiếu cũng không vỡ — đáng chú ý nhất là `PHOTOGRAPHER_NAME` (default `bebe`), quyết
định test calendar/booking chạy trên photographer nào của staging. Đổi biến này khi photographer
mặc định kín lịch hoặc bị xoá.

Biến set sẵn trong shell sẽ thắng `.env`, dùng để ghi đè tạm cho một lần chạy:

```powershell
$env:BASE_URL = "https://moi-truong-khac.fotowa.com"
$env:PHOTOGRAPHER_NAME = "bebe"
```

---

## Cài đặt

Toàn bộ câu lệnh là PowerShell, chạy từ thư mục gốc của dự án.

```powershell
# 1. venv + dependency (không cần `playwright install`, ta dùng Chrome hệ thống)
uv venv --python 3.13 --seed
uv pip install -r requirements.txt

# 2. cấu hình
Copy-Item .env.example .env
notepad .env

# 3. đăng nhập SSO tay một lần
.venv\Scripts\python.exe scripts\save_auth.py
```

Bước 3 mở một cửa sổ Chrome với profile automation riêng (`.auth/chrome-profile`). Bạn hoàn tất
đăng nhập Google; ngay khi trình duyệt quay về một trang fotowa là xong. Test dùng lại **đúng
profile đó**, nên có sẵn cookie SSO và — quan trọng không kém — disk cache của Chrome.

Vì sao cần cache: `assets/bundle/vendor.js` của staging nặng 10.5 MB và server không nén, lại là
blocking script trong `<head>`. Chạy với cache rỗng thì riêng việc mở trang chủ mất ~110s, vượt
timeout 30s của `goto` và cả suite fail ngay từ test đầu. Dùng lại profile thì còn ~1.8s.

Hệ quả cần nhớ: **đóng mọi cửa sổ Chrome đang mở profile này trước khi chạy test**, nếu không
`launch_persistent_context` sẽ báo profile bị khoá.

---

## Chạy test

```powershell
# kiểm tra tĩnh: --setup-plan + pyright, vài giây, không mở browser
.venv\Scripts\python.exe scripts\check.py

# tất cả test
.venv\Scripts\python.exe -m pytest

# chạy chậm để quan sát
.venv\Scripts\python.exe -m pytest --headed --slowmo 500

# một test case cụ thể
.venv\Scripts\python.exe -m pytest tests/test_user_01_login.py::TC_01_login_form_is_displayed
```

Không cần activate venv. Nếu vẫn muốn gọi `pytest` trực tiếp thì chạy `.\.venv\Scripts\Activate.ps1`
trước (thoát bằng `deactivate`).

---

## Những điều cần lưu ý

**Có hai lớp đăng nhập.** Cổng vào staging nằm sau Google SSO (AWS Cognito → Google IdP), không tự
động hoá được — phải chạy `scripts/save_auth.py`. Còn đăng nhập app fotowa ở `/users/sign_in` là
form email/password bình thường, fixture `logged_in` tự điền một lần cho cả session.

**Mọi fixture đều `scope="session"`** ⇒ các lần chạy diễn ra trong **một tab duy nhất**, mỗi test
tiếp tục từ nơi test trước để lại. Test chạy theo thứ tự khai báo và thứ tự đó có ý nghĩa; chạy
riêng một test sẽ bắt đầu từ `about:blank` nên test phụ thuộc test trước sẽ fail.

**Không có screenshot/trace khi fail.** `conftest.py` ghi đè fixture `context`/`page` của
pytest-playwright, làm vô hiệu hoá hook artifact dù `pytest.ini` đã bật. Muốn xem trực tiếp lúc
fail thì chạy `pytest --pdb` — Chrome vẫn sống và giữ nguyên state cho tới khi bạn thoát debugger.

**Fotowa render header hai
lần (desktop + mobile).**  selector ngây thơ sẽ báo `strict mode violation` vì Playwright chạy ở *strict mode*;  nên dùng selector duy nhất.

**Không gọi hành động trong `__init__` của page object.** Chỉ khai báo `Locator` lazy


**Timeout khi chờ form đăng nhập** nếu bị kẹt ở trang Google SSO tực session đã
lưu hết hạn, chạy lại `scripts/save_auth.py`.
