# Dự án Automation fotowa

Bộ test UI end-to-end cho dự án Fotowa, viết bằng
[Playwright](https://playwright.dev/python/) và pytest theo mô hình POM (Page Object Model).

---

## Cấu hình

| Công cụ | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.13 | `.venv` trong repo là CPython 3.13.13, bản native cho Windows |
| [uv](https://docs.astral.sh/uv/) | 0.11+ | Dùng để tạo venv và cài package (nhanh hơn `pip`, tự tải đúng bản Python) |
| pip | 26.2.1 | Có sẵn trong venv nhờ cờ `--seed`, dùng thay `uv` được nếu bạn quen hơn |
| Playwright | 1.62.0 | Cài kèm `pytest-playwright==0.6.2` trong `requirements.txt` |
| Google Chrome | 152.0.7977.77 | Test chạy trên Chrome đã cài trong máy (`channel="chrome"`), không dùng Chromium đi kèm |

Cần một tài khoản Google fotowa có quyền truy cập trang staging để làm được bất cứ việc gì sau
trang đăng nhập.

---

## Cài đặt

Toàn bộ câu lệnh dưới đây là PowerShell, chạy từ thư mục gốc của dự án.

### 1. Tạo virtualenv và cài dependency

```powershell
uv venv --python 3.13 --seed
uv pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium
```

### 2. Cấu hình biến môi trường

Copy file .env.example rồi điền giá trị của bạn:

```powershell
Copy-Item .env.example .env
notepad .env
```

`.env` đã được gitignore — tuyệt đối không commit file này.

| Biến | Giá trị mặc định | Mục đích |
|---|---|---|
| `BASE_URL` | **bắt buộc** | Site cần test, chỉ phần gốc không kèm path. Không có giá trị mặc định trong code — thiếu là test fail ngay |
| `TEST_EMAIL` | **bắt buộc** | Tài khoản staging; test nào cần tài khoản sẽ bị **skip** nếu để trống |
| `TEST_PASSWORD` | **bắt buộc** | tương tự như trên |
| `AUTH_DIR` | `.auth` | Nơi lưu dữ liệu session |
| `AUTH_STATE` | `.auth/storage_state.json` | Cookie đã lưu |
| `AUTOMATION_PROFILE_DIR` | `.auth/chrome-profile` | Chrome profile riêng cho `save_auth.py`, giúp Google nhớ bạn giữa các lần đăng nhập tay |
| `LOGIN_TIMEOUT_MS` | `300000` | Thời gian `save_auth.py` chờ bạn hoàn tất SSO |

Biến set sẵn trong shell sẽ thắng `.env`, nên bạn có thể ghi đè tạm thời cho một lần chạy:

```powershell
$env:BASE_URL = "https://moi-truong-khac.fotowa.com"
.venv\Scripts\python.exe -m pytest
```

### 3. Đăng nhập một lần

Trang staging nằm sau **Google SSO** (AWS Cognito → Google IdP), không thể tự động hoá bằng cách
điền form thông thường. Hãy đăng nhập tay một lần rồi tái sử dụng session:

```powershell
.venv\Scripts\python.exe scripts\save_auth.py
```

Một cửa sổ Chrome sẽ mở với profile automation riêng. Bạn hoàn tất đăng nhập Google; ngay khi
trình duyệt quay về một trang fotowa, cookie sẽ được ghi vào `.auth/storage_state.json` và
mọi test tự động dùng lại.


## Chạy test

Chuyển sang môi trường venv trước, mỗi lần mở terminal mới làm một lần:

```powershell
.\.venv\Scripts\Activate.ps1
```

Dấu hiệu thành công: đầu dòng lệnh xuất hiện tiền tố `(.venv)`. Sau đó gọi `pytest` trực tiếp:

```powershell
# chạy tất cả test files trong thư mục test/
pytest

# chạy test chạy chậm để quan sát
pytest --headed --slowmo 500

# chạy một test case cụ thể
pytest tests/test_login.py::test_login_form_is_displayed
```

Nếu không muốn activate, gọi thẳng `python.exe` trong venv — kết quả như nhau:

```powershell
.venv\Scripts\python.exe -m pytest
```

Gọi `pytest` mà chưa activate sẽ không chạy được — nó không có trong `PATH`. Thoát môi trường
venv bằng `deactivate`.

`pytest.ini` đã set sẵn `-v --browser chromium --screenshot only-on-failure
--tracing retain-on-failure`. Lưu ý: `conftest.py` ghi đè fixture `context`/`page` của
pytest-playwright để đưa context đã đăng nhập vào, việc này **vô hiệu hoá hook chụp
screenshot và tracing** — hiện tại các artifact đó không được tạo ra.

---

## Cấu trúc dự án

```
pages/          Page object — chỉ chứa locator và hành động ở mức trang
  login_page.py
tests/
  conftest.py   Fixture: dotenv, browser/context/page, login_page
  test_login.py
scripts/
  save_auth.py  Đăng nhập SSO tay một lần → .auth/storage_state.json
.auth/          Session đã lưu + Chrome profile automation (đã gitignore)
.env            Cấu hình local của bạn (đã gitignore)
.env.example    File mẫu được commit
pytest.ini
TODO.md         Các việc còn tồn
```

### Quy ước viết Page Object

- Locator được khai báo trong `__init__` dưới dạng `Locator` lazy. **Không bao giờ gọi một
  hành động** (`.click()`, `.fill()`, `.clear()`) ở đó — fixture khởi tạo object khi trang
  vẫn còn là `about:blank`, nên mọi hành động sẽ timeout 30 giây ngay trong fixture.
- Method `goto_*` để điều hướng, `expect_*` để assert, còn lại là hành động.
- Locator phải khớp đúng một element. Playwright chạy ở *strict mode*, nên một selector khớp
  hai node sẽ báo `strict mode violation` chứ không tự chọn một cái. fotowa render header
  hai lần (desktop + mobile), vậy nên hãy neo vào thứ gì đó duy nhất hoặc thêm `.first`.

### Các test dùng chung một tab trình duyệt

`browser_context`, `page` và `login_page` đều có **scope là session**, nên cả lần chạy diễn
ra trong một tab duy nhất. Mỗi test tiếp tục từ đúng nơi test trước để lại trình duyệt —
`test_login_with_valid_credentials` điền vào chính form mà `test_login_form_is_displayed`
đã điều hướng tới, không cần `goto` lần hai.

Những điều cần lưu ý:

- Test trong cùng một file chạy theo **thứ tự khai báo**, và thứ tự đó bây giờ có ý nghĩa.
  Di chuyển một test sẽ thay đổi trạng thái mà nó bắt đầu.
- Chạy riêng một test (`pytest -k valid_credentials`) sẽ bắt đầu từ `about:blank`, nên test
  nào phụ thuộc test trước sẽ fail khi chạy độc lập. Hãy thêm bước điều hướng riêng nếu bạn
  cần nó chạy độc lập được.
- Trạng thái được cố ý mang sang test sau: cookie, một modal đang mở, một form điền dở. Nếu
  một test cần trạng thái sạch, hãy điều hướng tường minh ở đầu test đó.

---

## Xử lý sự cố

**`403 Forbidden` từ `awselb/2.0`**
Chỉ xảy ra với User-Agent không phải trình duyệt — ví dụ `curl` mặc định. Đây *không phải*
chặn theo IP allowlist và không cần VPN. Với User-Agent của Chrome, site trả về 200 và
redirect sang Google SSO. (`TODO.md` vẫn mô tả đây là IP allowlist; ghi chú đó đã cũ.)

**Test bị skip với lý do "set TEST_EMAIL and TEST_PASSWORD"**
Điền hai giá trị đó vào `.env`.

**`strict mode violation: locator(...) resolved to 2 elements`**
Xem phần quy ước locator ở trên — thu hẹp selector hoặc dùng `.first`.

**Timeout khi chờ form đăng nhập**
Rất có thể bạn đang ở trang Google SSO, không phải form của fotowa. Chạy lại
`scripts/save_auth.py` — session đã lưu có lẽ đã hết hạn.

**`launch_persistent_context` fail / profile bị lock**
Đóng mọi cửa sổ Chrome đang dùng `.auth/chrome-profile` rồi thử lại.

---

## Ghi chú dọn dẹp

`.gitignore` hiện chỉ có `.auth/` và `.env`. `__pycache__/`, `.pytest_cache/`,
`test-results/` và `.venv/` vẫn đang được track và gây nhiễu diff — nên thêm vào.
