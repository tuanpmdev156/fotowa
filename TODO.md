# TODO

Các việc còn tồn của bộ test. Cập nhật lần cuối: 2026-09-11.

## Lưu ý khi viết test

- **Hai lớp đăng nhập.** Cổng staging là Google SSO, không tự động hoá được — chạy
  `scripts/save_auth.py` một lần. Đăng nhập app ở `/users/sign_in` thì fixture `logged_in` lo;
  cookie nằm ở `context` dùng chung nên nó tự short-circuit khi đã đăng nhập.
- **Mỗi test một tab, tự điều hướng.** `page` là function-scope, test nào cũng bắt đầu ở
  `about:blank` ⇒ dòng đầu tiên của test luôn là `goto_*`. Thứ tự chạy không có ý nghĩa;
  precondition đặt vào fixture, đừng dựa vào test trước.
- **Scope.** Chỉ fixture đắt và không giữ state mới `session` (`browser_context`, `context`,
  `credentials`, `available_slot`); hễ giữ `page` thì phải `function` — session-scope không xin
  được function-scope (`ScopeMismatch`).
- **Fail có screenshot, không có trace.** `_capture_screenshot` trong `conftest.py` ghi PNG
  full-page ra `test-results/<nodeid>-failed.png`. Muốn soi sống thì `pytest --pdb` — Chrome vẫn
  mở, giữ nguyên state.
- **Strict mode.** fotowa render header hai lần (desktop + mobile) ⇒ locator phải neo vào chỗ duy
  nhất, hoặc thêm `.first`.
- **Page object không gọi action trong `__init__`** — chỉ khai báo `Locator` lazy, không thì fixture
  ăn nguyên timeout 30s trên `about:blank`.
- **Timeout khi chờ form đăng nhập** = đang kẹt ở Google SSO, session đã hết hạn: chạy lại
  `scripts/save_auth.py`.

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

- [ ] **Tách test suite theo role (user / photographer).** Hiện chỉ có một tài khoản
      (`TEST_EMAIL`/`TEST_PASSWORD`). Khi thêm test cho photographer sẽ có hai role, hai tài
      khoản ⇒ chia như sau:

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

      - **`logged_in` phải chuyển xuống conftest con, xoá khỏi conftest gốc.** Lý do cũ (fixture
        session-scope chạy một lần rồi cache cho cả session) đã hết hiệu lực — `logged_in` giờ là
        function-scope. Nhưng vấn đề thật vẫn còn và nặng hơn: cookie nằm ở `context` **dùng
        chung**, nên role thứ hai vào sẽ thấy `is_logged_in()` true và short-circuit ngay, test
        pass với **sai tài khoản**. Hai hướng: mỗi conftest con có `logged_in` riêng **và**
        `_sign_in` phải đăng xuất trước khi tài khoản đang đăng nhập là role khác (cần cách đọc
        được email đang đăng nhập), hoặc chạy tách session (gạch đầu dòng dưới). Logic login chung
        vẫn để ở gốc (`_sign_in`), hai conftest con gọi lại — không copy-paste.
      - **Một lệnh chạy = một role**, chạy tuần tự (`scripts/run_all.py` hoặc `.ps1`: chạy
        `pytest tests/user` rồi `pytest tests/ph`, gộp exit code). Bắt buộc tuần tự vì
        `launch_persistent_context` **khoá** `.auth/chrome-profile`; hai process song song là fail.
        Mỗi lệnh là một session riêng ⇒ browser mới, login lại ⇒ hai thư mục không dính state
        của nhau. Đây là cách chắc chắn nhất tránh bẫy "cookie dùng chung" ở trên.
      - **Giữ nguyên `testpaths = tests`** cho `--collect-only` / `--setup-plan` (và
        `scripts/check.py`) hoạt động, nhưng **không chạy `pytest` trần nữa** — chạy trần sẽ gom
        cả hai thư mục vào một session, chung một tab và chung một `logged_in`. Đổi `testpaths`
        thành `tests/user tests/ph` không giải quyết gì: vẫn là một session.
      - **`pages/` không tách theo role**, chỉ tách theo trang. `LoginPage` dùng chung một form cho
        cả hai; chỉ thêm page object mới khi DOM thật sự khác (dashboard photographer...).

      Lưu ý khi làm:
      - Tên file test **không được trùng** giữa hai thư mục khi không có `__init__.py`
        (pytest báo `import file mismatch` — đã verify). Hoặc đặt tên khác nhau, hoặc thêm
        `__init__.py` vào cả hai.
      - Thư mục con và file được sort **xen kẽ theo alphabet** (`tests/admin/` chạy trước
        `tests/user/`) — đã verify. Không còn là vấn đề vì test đã độc lập, nhưng đừng dựa vào.
      - Thêm `PH_EMAIL` / `PH_PASSWORD` vào `.env.example`.
      - Nếu tài khoản photographer đăng nhập bằng Google khác thì cần profile SSO riêng
        (`AUTOMATION_PROFILE_DIR`), và phải chạy `save_auth.py` một lần cho profile đó — profile
        mới có cache rỗng nên lần đầu sẽ dính lại vụ `vendor.js` 10.5 MB / ~110s.

- [ ] Chưa chạy được headless / trên CI (`headless=False` hardcode trong `conftest.py`, và luồng
      Google SSO cần thao tác tay). Chỉ làm khi thật sự cần CI.


### DONE

- [x] **Screenshot khi test fail.** `conftest.py` ghi đè `context`/`page` nên fixture `new_context`
      của pytest-playwright — nơi plugin lưu artifact — không chạy; `--screenshot`/`--tracing` trong
      `pytest.ini` không sinh ra gì. Viết lại phần chụp ảnh: `_FAILED = pytest.StashKey[bool]()` +
      hook `pytest_runtest_makereport(wrapper=True)` đánh dấu node fail (tính cả `when == "setup"`,
      fixture hỏng cũng có ảnh), fixture `page` gọi `_capture_screenshot()` **trước**
      `page.close()`, ghi PNG full-page ra `<--output>/<nodeid>-{failed,finished}.png`
      (`test-results/`, đã gitignore), theo đúng ngữ nghĩa `--screenshot` của plugin (`on` chụp mọi
      test, `only-on-failure` chỉ chụp fail, `off` không chụp). Bắt `playwright.sync_api.Error`
      để lỗi teardown không che lỗi thật.
      **Không làm trace**: tracing gắn với `context` session-scope dùng chung ⇒ phải
      `start_chunk`/`stop_chunk` từng test và tab scratch của `available_slot` sẽ lọt vào chunk;
      không đáng lúc này. Đã gỡ `--tracing retain-on-failure` khỏi `pytest.ini` cho khỏi nói dối.
      **Verify:** `scripts/check.py` — pyright 0 lỗi. Đủ ba nhánh của `--screenshot`, chạy thật:
      `assert False` tạm trong `TC_01_login_form_is_displayed` ⇒ sinh `...-failed.png`, mở ra đúng
      trang login; `--screenshot on` với 2 test login pass ⇒ 2 file `...-finished.png`; mặc định
      (`only-on-failure`) mà test pass ⇒ `test-results/` không được tạo. Cả suite 9/9 pass 38.99s.

- [x] **Test độc lập — mỗi test một tab, tự điều hướng** (bước 1-6 của
      `plan/independent-tests.md`). `page` + các fixture page object `session` → `function`;
      `selected_slot` tách đôi thành `available_slot` (session, chỉ trả dữ liệu, tự mở/đóng tab
      scratch) và `selected_slot` (function, đường click thật, chỉ `TC_01` dùng); thêm
      `BookingRequestPage.goto_booking_request(slot)` vào thẳng bằng URL; `logged_in` →
      function-scope + fixture `logged_out` thay cho `clear_cookies` ngầm trong `browser_context`;
      4 test thêm `goto_*`; gỡ hẳn marker `incremental` (2 hook + `pytestmark` + entry `pytest.ini`).
      **Verify:** cả suite 9/9 pass 49.91s (trước ~20s), **và cả 9 test đều pass khi chạy rời**
      (5.5s-16.3s). `TC_05` chạy lẻ giờ pass — lỗi cũ (`-k TC_05` timeout trong
      `select_first_genre()`) tự hết. Ẩn số đã đóng: option card **có** render khi chưa chọn genre.

- [x] ~~**`ruff check` vào `scripts/check.py`**~~ — **đã gỡ bỏ khỏi dự án**: xoá `ruff.toml`,
      bỏ step `lint` trong `scripts/check.py`, bỏ `ruff==0.16.7` khỏi `requirements.txt` và gỡ khỏi
      `.venv`. `scripts/check.py` giờ chỉ còn 2 gate: `fixtures` + `types`. Kèm theo đó, nợ cũ
      10 `E501` cũng hết ý nghĩa.

- [x] **Toàn bộ locator về XPath `//`.** Ba chỗ còn CSS đã đổi: `genre_options` (`:visible` là
      pseudo-class CSS, không có trong XPath ⇒ tách ra `.filter(visible=True)`), `_option_card`
      (`has=` hoạt động với XPath, đã verify scope đúng), `_read_slot` (`xpath=./span` → `//span`).
      Verify trên Chrome: chained `parent.locator("//x")` **được** scope theo parent.

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
      *(Đã bị thay thế: `selected_slot` giờ là function-scope, xem mục test độc lập ở trên.)*
- [x] Bỏ hardcode photographer → env `PHOTOGRAPHER_NAME` + fixture `photographer_path`, dùng chung
      cho cả hai page object. Env phải đọc trong `conftest.py`, không đọc trong thân class.
- [x] `expect_selected_slot_in_url()` — assert path + `shooting_date`/`shooting_time` trong query.
      Pattern đã confirm trên staging (không phải `/reservations/`).
- [x] `scripts/save_auth.py` — lưu session Google SSO một lần.
- [x] Fixture `logged_in` — login qua form, short-circuit nếu đã login. *(Giờ là function-scope,
      phần logic nằm ở hàm `_sign_in`.)*
- [x] Bỏ heuristic "không thấy ログイン tức là đã login" (sai âm thầm). Neo vào `logged_in_marker`,
      tách 3 hàm: `is_logged_in()` (probe rẻ, `count()`), `expect_logged_in()` (retry),
      `expect_login_success()` (chỉ test dùng — notice chỉ hiện một lần).
- [x] ~~`DEFAULT_TIMEOUT_MS`~~ — revert, chỉ set lại đúng default 30s sẵn có của Playwright.
- [x] `browser_context` → `launch_persistent_context` trên `.auth/chrome-profile`: `vendor.js`
      10.5 MB không nén, cache rỗng ⇒ DOMContentLoaded 110s, cả suite fail; có cache 1.8s.
      Kèm xoá cookie `_session_id` (phải giữ `AWSELBAuthSessionCookie-*`) — nay nằm ở fixture
      `logged_out` chứ không còn chạy ngầm trong `browser_context`.
- [x] `scripts/check.py` — `--setup-plan` + `pyright` trong một lệnh.
- [x] Cập nhật `README.md` khớp code hiện tại.
- [x] Đọc ngày/giờ slot từ chính ô được bấm (`BookingSlot`), không hardcode ngày.
- [x] `pages/booking_request.py` hết stub — `expect_available_slot()` khớp format thật: ngày
      `2026/09/16` + khoảng giờ `08:00 - 09:00`.
- [x] Slot click pass trên browser thật — `SHOOTING_DURATION = 1h` đã xác nhận.
- [x] Marker `incremental` — test sau tự skip khi test trước cùng file fail.
      *(Đã gỡ bỏ: hết dùng chung tab thì nó chỉ còn giấu lỗi thật.)*
- [x] Calendar tự bấm 次週 tìm tuần có slot trống. Gate chờ render phải là `wait_for_function`
      (`not_to_have_text` pass sớm lúc Vue detach `td`); tuần vắt hai tháng có 2 `th[@colspan]`
      nên `_read_year_month()` phải cộng dồn colspan.
