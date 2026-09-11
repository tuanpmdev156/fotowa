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
profile đó**, nên có sẵn cookie SSO

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

# chụp màn hình mọi test, kể cả test pass
.venv\Scripts\python.exe -m pytest --screenshot on

# chỉ chụp test fail (mặc định của pytest.ini)
.venv\Scripts\python.exe -m pytest --screenshot only-on-failure

# tắt chụp màn hình 
.venv\Scripts\python.exe -m pytest --screenshot off

# đổi thư mục chứa ảnh( ví dụ: đổi thành artifacts) (mặc định test-results)
.venv\Scripts\python.exe -m pytest --output artifacts
```

Ảnh nằm trong `test-results/`, tên ghép từ nodeid: `...-failed.png` khi fail, `...-finished.png`
khi chụp lúc pass.



Activate venv
```powershell
.\.venv\Scripts\Activate.ps1
```
Exit venv
```powershell
deactivate
```
---

## Lưu ý khi viết test

Xem `TODO.md`, mục **Lưu ý khi viết test**.
