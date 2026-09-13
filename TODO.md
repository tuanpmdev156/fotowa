# TODO

Các việc còn tồn của bộ test. Cập nhật lần cuối: 2026-09-13.

## Lưu ý khi viết test

- **Hai lớp đăng nhập.** Cổng staging là Google SSO, không tự động hoá được — chạy `npm run auth`
  một lần. Đăng nhập app ở `/users/sign_in` thì fixture `loggedIn` lo; cookie nằm ở `context` dùng
  chung nên nó tự short-circuit khi đã đăng nhập.
- **Mỗi test một tab, tự điều hướng.** `page` là test-scope, test nào cũng bắt đầu ở `about:blank`
  ⇒ dòng đầu tiên của test luôn là `goto*`. Thứ tự chạy không có ý nghĩa; precondition đặt vào
  fixture, đừng dựa vào test trước.
- **Scope.** Chỉ fixture đắt và không giữ state mới `worker` (`persistentContext`, `appBaseUrl`,
  `appPhotographerPath`, `workerCredentials`, `availableSlot`); hễ giữ `page` thì phải `test` —
  worker-scope không xin được test-scope.
- **`workers: 1` là bắt buộc**, không phải tuỳ chọn: `launchPersistentContext` khoá độc quyền
  `.auth/chrome-profile`.
- **Thiếu `await` trước `expect` = assertion không chạy và test vẫn xanh.** `tsc` không bắt được.
  Cách duy nhất để chắc: phá assertion cho nó fail thật (verify hướng âm).
- **Fail có screenshot, chưa có trace.** Capture built-in của Playwright vẫn chạy dù ta ghi đè
  `context`/`page`, nên không cần code chụp ảnh thủ công như bản Python. Mỗi lần fail ra 2 PNG
  (tab trắng của persistent context + tab thật). Muốn trace thì `npx playwright test --trace on`;
  bật trace theo từng test qua config thì xem mục III.Infrastructure.
- **Không có cờ `--screenshot` ở CLI** (khác pytest-playwright) — đổi chế độ phải sửa
  `playwright.config.ts`.
- **Skip không lan truyền như pytest.** Fixture được resolve *trước* thân test, và worker fixture
  thì không skip được. Test cần credentials phải tự gọi `requireCredentials()` trong thân test,
  hoặc `skipWithoutCredentials()` trong `test.beforeEach`.
- **Strict mode.** fotowa render header hai lần (desktop + mobile) ⇒ locator phải neo vào chỗ duy
  nhất, hoặc thêm `.first()`.
- **Page object không gọi action trong constructor** — chỉ khai báo `Locator` lazy, không thì
  fixture ăn nguyên timeout 30s trên `about:blank`.
- **Đọc env chỉ qua `src/config/env.ts`**, và nó export **hàm** chứ không export hằng — hằng
  top-level sẽ đọc `process.env` trước khi dotenv kịp nạp.
- **Timeout khi chờ form đăng nhập** = đang kẹt ở Google SSO, session đã hết hạn: chạy lại
  `npm run auth`.

## I.USER

### Login

### Booking

- [ ] **Điền nốt form đặt lịch và submit.** `TC_05` giờ dừng ở verify phí đi xa, **chưa có TC nào
      bấm submit**. `confirmBookingButton = //button[@type='submit']` đã khai báo nhưng không ai
      dùng, và quá rộng: strict mode sẽ nổ nếu trang có nút submit thứ hai — neo lại theo text
      tiếng Nhật `確認・決済に進む` (đọc được từ `error-context.md` sinh ra khi chạy verify hướng âm).
      TC submit cần `expectSubmitted()` (assert đã rời `/private_offers/new`).
- [ ] **Trang review + thanh toán** (sau khi submit) — plan đầy đủ ở
      `planS/booking-confirm-payment.md`. Đang chặn ở Bước 0: chưa capture DOM nên chưa biết ô thẻ
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
      e2e/
        user/user-01-login.spec.ts, user-02-..., user-03-...
        ph/ph-01-....spec.ts
      src/fixtures/
        test.ts          # fixture chung: persistentContext, context, page, appBaseUrl,
                         # loginPage + hàm signIn() dùng chung. KHÔNG còn `loggedIn` ở đây.
        user.ts          # credentials + loggedIn cho user (TEST_EMAIL/TEST_PASSWORD)
        ph.ts            # credentials + loggedIn cho photographer (PH_EMAIL/PH_PASSWORD)
      ```

      Bốn quyết định đi kèm, mỗi cái đều có lý do cụ thể:

      - **`loggedIn` phải chuyển xuống fixture riêng của từng role.** Cookie nằm ở `context` **dùng
        chung**, nên role thứ hai vào sẽ thấy `isLoggedIn()` true và short-circuit ngay, test pass
        với **sai tài khoản**. Hai hướng: mỗi role có `loggedIn` riêng **và** `signIn()` phải đăng
        xuất trước khi tài khoản đang đăng nhập là role khác (cần cách đọc được email đang đăng
        nhập), hoặc chạy tách hẳn hai lần (gạch đầu dòng dưới). Logic login chung vẫn để ở
        `signIn()`, hai file gọi lại — không copy-paste.
      - **Một lệnh chạy = một role**, chạy tuần tự (`npm test -- e2e/user` rồi `npm test -- e2e/ph`,
        gộp exit code). Bắt buộc tuần tự vì `launchPersistentContext` **khoá**
        `.auth/chrome-profile`; hai process song song là fail — cũng chính là lý do `workers: 1`.
      - **Cân nhắc `projects` của Playwright** thay cho hai lệnh: hai project cùng `testDir` khác
        nhau, mỗi project một bộ fixture. Nhưng project chạy song song theo mặc định ⇒ vẫn phải
        `workers: 1`, nên lợi ích so với hai lệnh là không nhiều.
      - **`src/pages/` không tách theo role**, chỉ tách theo trang. `LoginPage` dùng chung một form
        cho cả hai; chỉ thêm page object mới khi DOM thật sự khác (dashboard photographer...).

      Lưu ý khi làm:
      - Thêm `PH_EMAIL` / `PH_PASSWORD` vào `.env.example` và vào `src/config/env.ts`.
      - Nếu tài khoản photographer đăng nhập bằng Google khác thì cần profile SSO riêng
        (`AUTOMATION_PROFILE_DIR`), và phải chạy `npm run auth` một lần cho profile đó — profile
        mới có cache rỗng nên lần đầu sẽ dính lại vụ `vendor.js` 10.5 MB / ~110s.

- [ ] **Trace theo từng test.** Giờ đã khả thi (`context.tracing.startChunk()/stopChunk()` trong
      fixture `page`), nhưng tab scratch của `availableSlot` chạy trong lúc setup fixture của test
      đầu tiên nên sẽ lọt vào chunk của test đó. Tạm thời dùng `--trace on` khi cần.

- [ ] Chưa chạy được headless / trên CI (`headless: false` trong `playwright.config.ts`, và luồng
      Google SSO cần thao tác tay). Chỉ làm khi thật sự cần CI.

### DONE

> Các mục dưới đây trước mốc "Port sang TypeScript" mô tả bộ test cũ viết bằng Python/pytest.
> Tên file/hàm trong đó giữ nguyên làm tư liệu lịch sử.

- [x] **Port toàn bộ suite từ Python/pytest sang TypeScript/`@playwright/test`.** Plan ở
      `planS/typescript-migration.md`. `pages/` + `tests/` → `src/pages/` + `src/fixtures/` + `e2e/`;
      `conftest.py` → `src/fixtures/test.ts` + `src/config/env.ts` + `playwright.config.ts`;
      `scripts/check.py` → `npm run check` (`tsc --noEmit` + `playwright test --list`);
      `save_auth.py` → `scripts/save-auth.ts` (chạy bằng `tsx`: type-stripping của Node 24 không đổi
      `import` thành `require`); `fixtures/` → `dom-snapshots/`. Toàn bộ ~45 XPath giữ nguyên.
      Gỡ được `_capture_screenshot` + hook `pytest_runtest_makereport` (~30 LOC) vì capture built-in
      của Playwright **vẫn chạy** dù ghi đè `context`/`page` — đã đo cả 3 chế độ. Thêm
      `fullPage: true` cho khớp bản Python. Hai fix gộp kèm: `hasLongDistanceFeeWarning()` có
      timeout 5s (trước đốt đủ 30s mới skip) và bắt đúng `errors.TimeoutError` thay vì `catch` trần.
      **Verify:** `npm run check` sạch, liệt kê đúng 9 test; cả suite **9/9 pass 44.1s**; **cả 9
      test pass khi chạy rời** (5.1s–11.8s); verify hướng âm 4/4 (phá `LOGIN_SUCCESS_MESSAGE`,
      `expectCalendarLoaded`, `expectTotal`, nhãn `priceCell` ⇒ đều fail thật, không có assertion
      nào bị nuốt vì thiếu `await`); đối chiếu `pytest -rs` cùng lúc: 9 passed 48.21s, cùng pattern.

- [x] **Screenshot khi test fail.** `conftest.py` ghi đè `context`/`page` nên fixture `new_context`
      của pytest-playwright — nơi plugin lưu artifact — không chạy; `--screenshot`/`--tracing` trong
      `pytest.ini` không sinh ra gì. Viết lại phần chụp ảnh: `_FAILED = pytest.StashKey[bool]()` +
      hook `pytest_runtest_makereport(wrapper=True)` đánh dấu node fail (tính cả `when == "setup"`,
      fixture hỏng cũng có ảnh), fixture `page` gọi `_capture_screenshot()` **trước**
      `page.close()`, ghi PNG full-page ra `<--output>/<nodeid>-{failed,finished}.png`.
      *(Đã bị thay thế: capture built-in của `@playwright/test` lo hết, xem mục port ở trên.)*

- [x] **Test độc lập — mỗi test một tab, tự điều hướng** (bước 1-6 của `planS/independent-tests.md`,
      file plan đã xoá). `page` + các fixture page object `session` → `function`; `selected_slot`
      tách đôi thành `available_slot` (session, chỉ trả dữ liệu, tự mở/đóng tab scratch) và
      `selected_slot` (function, đường click thật, chỉ `TC_01` dùng); thêm
      `BookingRequestPage.goto_booking_request(slot)` vào thẳng bằng URL; `logged_in` →
      function-scope + fixture `logged_out` thay cho `clear_cookies` ngầm trong `browser_context`;
      gỡ hẳn marker `incremental`. **Verify:** cả suite 9/9 pass 49.91s, **và cả 9 test đều pass khi
      chạy rời**. Ẩn số đã đóng: option card **có** render khi chưa chọn genre.

- [x] ~~**`ruff check` vào `scripts/check.py`**~~ — **đã gỡ bỏ khỏi dự án**. Không thêm linter mới
      khi chưa được yêu cầu.

- [x] **Toàn bộ locator về XPath `//`.** Ba chỗ còn CSS đã đổi: `genre_options` (`:visible` là
      pseudo-class CSS, không có trong XPath ⇒ tách ra `.filter(visible=True)`), `_option_card`
      (`has=` hoạt động với XPath, đã verify scope đúng), `_read_slot` (`xpath=./span` → `//span`).
      Verify trên Chrome: chained `parent.locator("//x")` **được** scope theo parent.

- [x] **遠方出張料 (phí di chuyển xa) hiển thị và được cộng vào tổng.** `TC_05`: chọn genre →
      `select_filming_location()` → gate `has_long_distance_fee_warning()` (không có cảnh báo thì
      `skip`, vì địa điểm không phát sinh phí là dữ liệu hợp lệ) → `expect_long_distance_fee_charged()`
      → `expect_payment_table_matches_selection()` lo phần tổng. Kế hoạch + lý do ở
      `planS/booking-price-check.md`. Số đọc được lúc verify hướng âm:
      `撮影料金 ¥24,200 + 遠方出張料 ¥3,000 = 合計 ¥27,200`.

- [x] Giá tiền trang đặt lịch, cả hai nhánh (không/có option): `read_option_cards()`,
      `sum_subtotal()`, `expect_total()`, `expect_payment_table_matches_selection()`. Kỳ vọng tính
      từ giá đọc trên trang, không hardcode.
- [x] Bỏ hardcode photographer → env `PHOTOGRAPHER_NAME`, dùng chung cho cả hai page object.
- [x] `expect_selected_slot_in_url()` — assert path + `shooting_date`/`shooting_time` trong query.
- [x] `scripts/save_auth.py` — lưu session Google SSO một lần.
- [x] Fixture `logged_in` — login qua form, short-circuit nếu đã login.
- [x] Bỏ heuristic "không thấy ログイン tức là đã login" (sai âm thầm). Neo vào `logged_in_marker`,
      tách 3 hàm: `is_logged_in()` (probe rẻ, `count()`), `expect_logged_in()` (retry),
      `expect_login_success()` (chỉ test dùng — notice chỉ hiện một lần).
- [x] ~~`DEFAULT_TIMEOUT_MS`~~ — revert, chỉ giữ đúng default 30s sẵn có của Playwright.
- [x] `browser_context` → `launch_persistent_context` trên `.auth/chrome-profile`: `vendor.js`
      10.5 MB không nén, cache rỗng ⇒ DOMContentLoaded 110s, cả suite fail; có cache 1.8s.
      Kèm xoá cookie `_session_id` (phải giữ `AWSELBAuthSessionCookie-*`).
- [x] `scripts/check.py` — `--setup-plan` + `pyright` trong một lệnh.
- [x] Cập nhật `README.md` khớp code hiện tại.
- [x] Đọc ngày/giờ slot từ chính ô được bấm (`BookingSlot`), không hardcode ngày.
- [x] `expect_available_slot()` khớp format thật: ngày `2026/09/16` + khoảng giờ `08:00 - 09:00`.
- [x] Marker `incremental` — test sau tự skip khi test trước cùng file fail.
      *(Đã gỡ bỏ: hết dùng chung tab thì nó chỉ còn giấu lỗi thật.)*
- [x] Calendar tự bấm 次週 tìm tuần có slot trống. Gate chờ render phải là `wait_for_function`
      (`not_to_have_text` pass sớm lúc Vue detach `td`); tuần vắt hai tháng có 2 `th[@colspan]`
      nên `_read_year_month()` phải cộng dồn colspan.
