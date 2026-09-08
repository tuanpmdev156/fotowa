# TODO

Các việc còn tồn của bộ test. Cập nhật lần cuối: 2026-09-08.

## I.USER

### Login

- [ ] Chưa có test đăng nhập sai. `LoginPage.expect_error` và `expect_still_on_login_page` đã viết
      xong nhưng **chưa test nào dùng** — thêm `test_login_with_invalid_credentials`.

- [ ] `is_logged_in()` suy ra trạng thái từ việc login link ログイン còn hiện hay không. Đủ dùng, nhưng
      nếu header đổi thì test sẽ sai âm thầm — cân nhắc neo vào một element chỉ có khi đã đăng nhập.

### Booking

- [ ] **`pages/booking_request.py` mới chỉ là stub.** Locator `selected_datetime`
      (`//*[contains(@class,'selectedDateTime')]`) là placeholder, và `expect_slot` đang *đoán*
      format tiếng Nhật (`2026年9月10日` + `09:00` nằm chung một element). Lấy XPath và format
      thật từ DevTools trên trang đích.
      → `test_selected_slot_is_shown_on_booking_page` **không thể pass** cho tới khi xong việc này.
- [ ] Assert URL của trang đích. Path là dynamic (tới đây bằng click, không bằng `goto`), nên
      dùng regex: `expect(self.page).to_have_url(re.compile(r"/reservations/"))` — xác nhận
      pattern thật trước.
- [ ] Điền nốt form đặt lịch và submit (mới chỉ dừng ở bước chọn slot trên calendar).

## II.PH

### Profile

- [ ] `PATH = "/photographers/bebe"` đang hardcode một photographer trên staging. Chỉ tham số hóa
      khi thật sự cần test nhiều photographer (YAGNI).
- [ ] Chưa có test cho trường hợp calendar **không có** slot trống nào —
      `select_first_available_slot()` raise `AssertionError`, cần quyết định đó có phải hành vi
      mong muốn không.



## III.Infrastructure

- [ ] **`--screenshot` / `--tracing` trong `pytest.ini` không tạo ra artifact nào.** `conftest.py`
      ghi đè `context`/`page` của pytest-playwright nên fixture `new_context` của plugin bị bỏ qua.
      Đang chấp nhận đánh đổi; nếu cần artifact thì phải tự gọi `context.tracing.start/stop`.
- [ ] `USE_CHROME_PROFILE` trong `.env.example` là **biến chết** — không có code nào đọc. Xóa đi
      hoặc implement nhánh dùng persistent profile.
- [ ] Fixture đều `scope="session"` ⇒ chạy chung một tab, thứ tự test là load-bearing. Chưa có
      cách chạy độc lập một test bất kỳ. Nếu sau này thấy vướng thì thêm bước điều hướng tường
      minh ở đầu mỗi test.
- [ ] Chưa chạy được headless / trên CI (`headless=False` hardcode trong `conftest.py`, và luồng
      Google SSO cần thao tác tay). Chỉ làm khi thật sự cần CI.


### DONE

- [x] Lưu session Google SSO một lần bằng `scripts/save_auth.py` → `.auth/storage_state.json`.
- [x] Fixture `logged_in`: đăng nhập qua form một lần cho cả session, short-circuit nếu test đăng nhập chạy trước đã login rồi.
- [x] Gom timeout về một chỗ trong fixture `page` (`DEFAULT_TIMEOUT_MS`, áp cho cả action, navigation và `expect`).
- [x] `scripts/check.py`: `pytest --setup-plan` + `pyright` trong một lệnh, bắt lỗi sai tên fixture và sai kiểu mà không cần mở browser.
- [x] Cập nhật lại `README.md` cho khớp code hiện tại (tên file page object, bỏ bước
      `playwright install`, thêm `scripts/check.py` + `DEFAULT_TIMEOUT_MS`, xoá mục "Ghi chú dọn
      dẹp" đã sai).
- [x] Đọc ngày/giờ của slot từ chính ô được bấm (`BookingSlot`) thay vì hardcode ngày.
