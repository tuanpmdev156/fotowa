# TODO

Các việc còn tồn của bộ test. Cập nhật lần cuối: 2026-09-11.

## I.USER

### Login

### Booking

- [ ] **Điền nốt form đặt lịch và submit.** `TC_05` giờ dừng ở verify phí đi xa, **chưa có TC nào
      bấm submit**. `confirm_booking_button = //button[@type='submit']` đã khai báo nhưng không ai
      dùng, và quá rộng: strict mode sẽ nổ nếu trang có nút submit thứ hai — neo lại theo text
      tiếng Nhật `確認・決済に進む` (đọc được từ accessibility dump khi chạy verify hướng âm).
      TC submit cần `expect_submitted()` (assert đã rời `/private_offers/new`).
- [ ] **Trang review + thanh toán** (sau khi submit) — plan đầy đủ ở
      `plan/booking-confirm-payment.md`. Đang chặn ở Bước 0: chưa capture DOM nên chưa biết ô thẻ
      là input thường hay iframe cổng thanh toán. Đã chốt: đặt đơn thật trên staging, **huỷ tay** —
      khi làm tới đây, mỗi lần chạy cả suite sinh một đơn và ăn mất một slot của
      `PHOTOGRAPHER_NAME`.

## II.PH

### Profile



## III.Infrastructure

- [ ] **Tách test suite theo role (user / photographer).** Hiện tất cả test nằm phẳng trong
      `tests/` và chỉ có một tài khoản (`TEST_EMAIL`/`TEST_PASSWORD`). Khi thêm test cho
      photographer sẽ có hai role, hai tài khoản ⇒ chia như sau:

      ```
      tests/
        conftest.py        # fixture chung: browser_context, page, base_url, login_page,
                           # + hàm/factory login dùng chung. KHÔNG còn `logged_in` ở đây.
        user/conftest.py   # credentials + logged_in cho user (TEST_EMAIL/TEST_PASSWORD)
        user/test_01_login.py, test_02_photographer_profile.py, test_03_booking_request.py
        ph/conftest.py     # credentials + logged_in cho photographer (PH_EMAIL/PH_PASSWORD)
        ph/test_01_...py
      ```

      Bốn quyết định đi kèm, mỗi cái đều có lý do cụ thể:

      - **`logged_in` phải chuyển xuống conftest con, xoá khỏi conftest gốc.** Đây là điểm dễ sai
        nhất: fixture `scope="session"` ở gốc chỉ **chạy một lần rồi cache** cho cả session, bất kể
        ai gọi. Nếu chỉ override `credentials` ở conftest con mà để `logged_in` ở gốc, thì khi hai
        thư mục chạy chung một session, thư mục thứ hai dùng lại phiên đăng nhập của thư mục thứ
        nhất — và `is_logged_in()` short-circuit sẽ che luôn lỗi này, test pass với sai tài khoản.
        Đặt `logged_in` ở mỗi conftest con thì mỗi role là một FixtureDef riêng, đúng cả khi chạy
        tách lẫn chạy gộp. Logic login chung vẫn để ở gốc, hai conftest con gọi lại — không
        copy-paste.
      - **Một lệnh chạy = một role**, chạy tuần tự (`scripts/run_all.py` hoặc `.ps1`: chạy
        `pytest tests/user` rồi `pytest tests/ph`, gộp exit code). Bắt buộc tuần tự vì
        `launch_persistent_context` **khoá** `.auth/chrome-profile`; hai process song song là fail.
        Mỗi lệnh là một session riêng ⇒ browser mới, `_session_id` clear lại, login lại ⇒ hai
        thư mục không dính state của nhau và thứ tự giữa hai thư mục không còn là vấn đề.
      - **Giữ nguyên `testpaths = tests`** cho `--collect-only` / `--setup-plan` (và
        `scripts/check.py`) hoạt động, nhưng **không chạy `pytest` trần nữa** — chạy trần sẽ gom
        cả hai thư mục vào một session, chung một tab và chung một `logged_in`. Đổi `testpaths`
        thành `tests/user tests/ph` không giải quyết gì: vẫn là một session.
      - **`pages/` không tách theo role**, chỉ tách theo trang. `LoginPage` dùng chung một form cho
        cả hai; chỉ thêm page object mới khi DOM thật sự khác (dashboard photographer...).

      Lưu ý khi làm:
      - Tên file test **không được trùng** giữa hai thư mục khi không có `__init__.py`
        (pytest báo `import file mismatch`). Hoặc đặt tên khác nhau, hoặc thêm `__init__.py`
        vào cả hai.
      - Thêm `PH_EMAIL` / `PH_PASSWORD` vào `.env.example`.
      - Nếu tài khoản photographer đăng nhập bằng Google khác thì cần profile SSO riêng
        (`AUTOMATION_PROFILE_DIR`), và phải chạy `save_auth.py` một lần cho profile đó — profile
        mới có cache rỗng nên lần đầu sẽ dính lại vụ `vendor.js` 10.5 MB / ~110s.

- [ ] **`--screenshot` / `--tracing` trong `pytest.ini` không tạo ra artifact nào.** `conftest.py`
      ghi đè `context`/`page` của pytest-playwright nên fixture `new_context` của plugin bị bỏ qua.
      Đang chấp nhận đánh đổi; nếu cần artifact thì phải tự gọi `context.tracing.start/stop`.
- [ ] `USE_CHROME_PROFILE` trong `.env.example` là **biến chết** — không có code nào đọc. Xóa đi
      hoặc implement nhánh dùng persistent profile.
- [ ] Chưa chạy được headless / trên CI (`headless=False` hardcode trong `conftest.py`, và luồng
      Google SSO cần thao tác tay). Chỉ làm khi thật sự cần CI.


### DONE

- [x] **遠方出張料 (phí di chuyển xa) hiển thị và được cộng vào tổng.** `TC_05_long_distance_fee_in_payment_table`:
      chọn genre → `select_filming_location()` → gate `has_long_distance_fee_warning()` (không có
      cảnh báo thì `skip`, vì địa điểm không phát sinh phí là dữ liệu hợp lệ) →
      `expect_long_distance_fee_charged()` (dòng `遠方出張料` có, tiền > 0) →
      `expect_payment_table_matches_selection()` lo phần tổng. Gộp `_get_option_price` thành
      `_price_cell(label)` một tham số, lọc theo nhãn `th`, không lọc theo class của `tr`.
      Kế hoạch + lý do ở `plan/booking-price-check.md`.
      **Verify:** cả suite 9/9 pass (2 run), `TC_05` chạy thật chứ không `SKIPPED` (`-rs` không có
      dòng skip nào) ⇒ locator cảnh báo `longDistanceFee` là thật. Hướng âm: đổi nhãn thành
      `遠方出張料X` ⇒ fail đúng ở `booking_request.py:192`, không phải skip. Số đọc được lúc fail:
      `撮影料金 ¥24,200 + 遠方出張料 ¥3,000 = 合計 ¥27,200` ⇒ phí đi xa nằm trong tổng.

- [x] Giá tiền trang đặt lịch, cả hai nhánh (không/có option): `read_option_cards()`,
      `read_subtotal()`, `expect_total()`, `expect_payment_table_matches_selection()`. Locator
      thuần, đã xoá 2 hằng JS `evaluate_all`. Kỳ vọng tính từ giá đọc trên trang, không hardcode.
      Verify 3/3 pass staging.
- [x] Precondition trang private offer vào fixture `selected_slot` (session scope) ⇒
      `test_user_03` chạy lẻ được; `test_user_02::TC_02` thì chưa.
- [x] Bỏ hardcode photographer → env `PHOTOGRAPHER_NAME` + fixture `photographer_path`, dùng chung
      cho cả hai page object. Env phải đọc trong `conftest.py`, không đọc trong thân class.
- [x] `expect_selected_slot_in_url()` — assert path + `shooting_date`/`shooting_time` trong query.
      Pattern đã confirm trên staging (không phải `/reservations/`).
- [x] `scripts/save_auth.py` — lưu session Google SSO một lần.
- [x] Fixture `logged_in` — login qua form một lần cho cả session, short-circuit nếu đã login.
- [x] Bỏ heuristic "không thấy ログイン tức là đã login" (sai âm thầm). Neo vào `logged_in_marker`,
      tách 3 hàm: `is_logged_in()` (probe rẻ, `count()`), `expect_logged_in()` (retry),
      `expect_login_success()` (chỉ test dùng — notice chỉ hiện một lần).
- [x] ~~`DEFAULT_TIMEOUT_MS`~~ — revert, chỉ set lại đúng default 30s sẵn có của Playwright.
- [x] `browser_context` → `launch_persistent_context` trên `.auth/chrome-profile`: `vendor.js`
      10.5 MB không nén, cache rỗng ⇒ DOMContentLoaded 110s, cả suite fail; có cache 1.8s.
      Kèm xoá cookie `_session_id` mỗi run (phải giữ `AWSELBAuthSessionCookie-*`).
- [x] `scripts/check.py` — `--setup-plan` + `pyright` trong một lệnh.
- [x] Cập nhật `README.md` khớp code hiện tại.
- [x] Đọc ngày/giờ slot từ chính ô được bấm (`BookingSlot`), không hardcode ngày.
- [x] `pages/booking_request.py` hết stub — `expect_available_slot()` khớp format thật: ngày
      `2026/09/16` + khoảng giờ `08:00 - 09:00`.
- [x] Slot click pass trên browser thật — `SHOOTING_DURATION = 1h` đã xác nhận.
- [x] Marker `incremental` — test sau tự skip khi test trước cùng file fail.
- [x] Calendar tự bấm 次週 tìm tuần có slot trống. Gate chờ render phải là `wait_for_function`
      (`not_to_have_text` pass sớm lúc Vue detach `td`); tuần vắt hai tháng có 2 `th[@colspan]`
      nên `_read_year_month()` phải cộng dồn colspan.
