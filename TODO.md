# TODO

Các việc còn tồn của bộ test. Cập nhật lần cuối: 2026-09-09.

## I.USER

### Login

- [ ] `is_logged_in()` suy ra trạng thái từ việc login link ログイン còn hiện hay không. Đủ dùng, nhưng
      nếu header đổi thì test sẽ sai âm thầm — cân nhắc neo vào một element chỉ có khi đã đăng nhập.

### Booking

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
- [ ] Fixture đều `scope="session"` ⇒ chạy chung một tab, thứ tự test là load-bearing. Marker
      `incremental` đã chặn test sau chạy khi test trước fail, nhưng **chạy độc lập một test
      vẫn không được** (pytest không tự chạy test đứng trước). Nếu cần, chuyển precondition
      (`goto_profile_page` + `expect_calendar_loaded`) vào một fixture `calendar_ready`.
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
- [x] `pages/booking_request.py` hết là stub: locator thật
      (`//div[@id='app']//div[@class='shootingDateTimeControl__details']`) và `expect_slot` khớp
      format thật của trang đích — ngày `2026/09/16` (zero-pad) và khoảng giờ `08:00 - 09:00`
      (giờ đã chọn + 1 tiếng). Assert cả giờ bắt đầu lẫn kết thúc nên không false-pass khi
      click sai ô.
- [x] `test_03_select_first_available_slot` chạy pass trên browser thật: locator
      `shootingDateTimeControl__details` và giả định `SHOOTING_DURATION = 1h` đã được xác nhận,
      không còn là suy đoán.
- [x] Marker `incremental` (hook trong `tests/conftest.py` + đăng ký trong `pytest.ini`):
      test sau tự skip kèm lý do khi test trước trong cùng file fail, thay vì fail dây chuyền
      với lỗi khó đọc. Bật cho `tests/test_photographer_profile.py` bằng `pytestmark`.
- [x] Calendar tự bấm 次週 tìm tuần có slot trống (`goto_next_week()` +
      `goto_week_with_available_date()`, `MAX_WEEKS = 4`), locator `//li[@class='next']/a`.
      Hai chỗ suýt sai đã sửa và verify trên staging:
      - Gate chờ render **không** dùng được `expect(...).not_to_have_text(...)`: lúc Vue render
        lại, `td` biến mất trong chốc lát và assert phủ định coi "không có element" là thoả nên
        pass sớm, đọc ngay sau đó vẫn ra tuần cũ. Thay bằng `page.wait_for_function` đòi ô ngày
        đầu vừa tồn tại vừa khác giá trị cũ (`_FIRST_DAY_CHANGED`, viết gọn bằng
        `?.innerText.trim() ?? old` để `td` chưa render bị coi là "chưa đổi").
      - Tuần vắt qua hai tháng có **hai** `th[@colspan]` (`colspan=3` "2026/09" + `colspan=4`
        "2026/10") ⇒ `_read_year_month()` cũ vỡ vì strict mode, và nếu không vỡ cũng gán sai
        tháng cho 4 cột cuối. Giờ nhận `column` và cộng dồn colspan để tra đúng ô.
      Verify: tuần đầu 0 slot → bấm 3 lần → chọn ô 2026/10/03 08:00, trang booking khớp.
      Chạy lại pass sau khi rút gọn `_FIRST_DAY_CHANGED`.
