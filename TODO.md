# TODO

Các việc còn tồn của bộ test. Cập nhật lần cuối: 2026-09-09.

## I.USER

### Login

### Booking

- [ ] Kiểm tra giá tiền cuối cùng trên trang đặt lịch, cả hai nhánh:
      - **Không chọn option phụ** — tổng tiền = giá cơ bản của plan.
      - **Có chọn option phụ** — tổng tiền = giá cơ bản + tổng giá các option đã tick, và
        tổng phải cập nhật lại ngay khi tick/bỏ tick (tính lại ở client).
      Tính kỳ vọng từ chính giá đọc trên trang (như `BookingSlot`), **không hardcode** con số —
      giá plan/option trên staging đổi được. Cần confirm locator thật của khối tổng tiền +
      danh sách option trước khi viết assert.
- [ ] Điền nốt form đặt lịch và submit (mới chỉ dừng ở bước chọn slot trên calendar).

## II.PH

### Profile

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

- [x] Bỏ hardcode photographer trong `pages/photographer_profile.py`. Giờ đọc từ env
      `PHOTOGRAPHER_NAME` (default `bebe`, thiếu biến thì test vẫn chạy như cũ); fixture
      `photographer_path` dựng ra `/photographers/<slug>` và truyền vào **cả**
      `PhotographerProfilePage` (để `goto`) lẫn `BookingRequestPage` (để assert URL trang private
      offer) ⇒ slug chỉ viết một lần cho cả suite. `PATH`/`PATH_PATTERN` ở cấp class bị bỏ, thay
      bằng `self.path` / `self.path_pattern`.
      - **Env phải đọc trong `conftest.py`, không đọc trong thân class của page object.**
        `conftest` `import pages...` **trước** khi gọi `load_dotenv()`, nên `os.getenv` trong thân
        class chạy lúc `.env` chưa được nạp — nó chỉ thấy biến set sẵn trong shell và âm thầm rơi
        về default. Đây là lý do `PHOTOGRAPHER_NAME` nằm cạnh `DEFAULT_TIMEOUT_MS` chứ không nằm
        trong page object.
      - Constant `PATH` cấp class (và comment đi kèm đã lệch với code) bị xoá.
      Verify: `pytest` 5/5 pass với default. Override thật cũng đã kiểm —
      `PHOTOGRAPHER_NAME=zzz-no-such-photographer pytest ...::test_01` fail vì trang trả về error
      page của Rails, chứng minh biến env thật sự đi vào URL chứ không bị bỏ qua.

- [x] Assert URL trang đích sau khi bấm slot (`expect_selected_slot_in_url()` trong
      `pages/booking_request.py`). Pattern thật đã xác nhận trên staging — không phải
      `/reservations/` như phỏng đoán cũ:
      `{base_url}/photographers/<slug>/private_offers/new?shooting_date=2026-10-03&shooting_time=08:00`.
      - Ngày/giờ của slot nằm ngay trong query string nên URL khẳng định được cả "đúng trang" lẫn
        "app nhận đúng ô vừa bấm". Việc này **trùng** với `expect_available_slot()` (trang đích
        render text ngày/giờ từ chính hai param này) — trùng có ý, đổi lại thông báo lỗi chỉ
        đúng ngày/giờ sai thay vì `element(s) not found` sau 30s.
      - Path lấy từ fixture `photographer_path` (`self.path_pattern`), không hardcode slug lần
        thứ hai ⇒ đổi photographer chỉ sửa một chỗ, và assert bắt luôn trường hợp nhảy sang
        photographer khác.
      - Không neo `$` ở cuối regex: app có thể thêm param mới.
      - `test_03` gọi `expect_selected_slot_in_url()` **trước** `expect_available_slot()`; thứ tự là
        load-bearing.
      Verify: `pytest` 5/5 pass. Kiểm cả nhánh phủ định — tạm đổi `path_pattern` thành
      `private_offer_x` thì `test_03` fail đúng ở dòng `expect_selected_slot_in_url()`, và URL actual in ra
      xác nhận `:` trong `shooting_time=08:00` **không** bị percent-encode, thứ tự param là
      `shooting_date` rồi `shooting_time`.

- [x] Lưu session Google SSO một lần bằng `scripts/save_auth.py` → `.auth/storage_state.json`.
- [x] Fixture `logged_in`: đăng nhập qua form một lần cho cả session, short-circuit nếu test đăng nhập chạy trước đã login rồi.
- [x] Bỏ heuristic "không thấy link ログイン tức là đã login" — suỷ luận phủ định này sai
      âm thầm: header đổi class/text là locator không match, `is_visible()` trả `False`, và
      test báo "đã login" trong khi chưa. Giờ neo vào `logged_in_marker` =
      `//a[@href='/users/sign_out' and @data-ga-label='sign-out']` — link ログアウト mà server
      chỉ render khi đã đăng nhập. Tách làm ba vì một hàm không gánh được cả hai vai:
      - `is_logged_in()` — probe rẻ cho fixture ngắn mạch, dùng `count() > 0`, không retry.
        Dùng `expect()` ở đây thì lúc chưa login phải chờ hết 30s mới biết, mà đó là
        trường hợp bình thường. Cũng không dùng `is_visible()`: header render hai lần
        (desktop + hamburger) và bản desktop nằm trong dropdown ẩn nên `visible=false`.
      - `expect_logged_in()` — assert có retry (`to_be_attached()` trên `.first`), dùng trong
        fixture `logged_in` và test.
      - `expect_login_success()` — assert hành vi ngay sau submit: URL tự về home
        (`re.compile(rf"^{re.escape(base_url)}/?$")`) + `div.globalNotice > p.globalNotice__description`
        có text `ログインに成功しました`. Chỉ test dùng, không đưa vào fixture vì thông báo chỉ hiện một lần.
      Verify: `pytest` — 5/5 pass; chạy riêng `tests/test_photographer_profile.py` setup 10.6s
      (không treo 30s) xác nhận nhánh probe-chưa-login vẫn nhanh.
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
