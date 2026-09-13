# Plan: trang review + thanh toán (sau `TC_05_fill_and_submit_booking_form`)

**Trạng thái:** chưa bắt đầu. Viết ngày 2026-09-11.

Sau khi `TC_05` bấm `confirm_booking_button`, app chuyển sang trang **review đơn + nhập thẻ**.
Trang này **chưa có DOM trong `fixtures/`**, nên mọi locator dưới đây là *chỗ để điền*, không phải
locator thật. Bước 0 là bắt buộc — không đoán selector.

**Quyết định đã chốt:** test **đặt đơn thật** trên staging, cleanup (huỷ đơn) làm **tay**.
⇒ mỗi lần chạy cả suite sinh một đơn thật. Xem *Hệ quả của việc đặt thật* bên dưới.

---

## Bước 0 — Capture DOM trước (chặn mọi bước sau)

Không có DOM thì không biết: thẻ là input thường hay **iframe** của cổng thanh toán
(Stripe/GMO/Veritrans → phải dùng `frame_locator`, khác hẳn về code), tài khoản test đã lưu thẻ sẵn
chưa, trang review có mấy `button[type=submit]`, có bước xác nhận kép không.

Cách làm, không cần viết script mới:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_user_03_booking_request.py --pdb
```

Teardown bị hoãn khi vào pdb ⇒ cửa sổ Chrome đứng nguyên ở trang review. Trong pdb:

```python
open(r"fixtures/booking_confirm.html", "w", encoding="utf-8").write(
    booking_request_page.page.locator("//div[@id='app']").inner_html()
)
booking_request_page.page.url
```

(Tạm thêm `assert False` ở cuối `TC_05` để pdb dừng đúng chỗ, xoá lại sau.)

Lưu **cả hai**: `fixtures/booking_confirm.html` (trang review) và — nếu đi hết được —
`fixtures/booking_complete.html` (trang hoàn tất). Ghi `page.url` của từng trang vào mục *Ẩn số*
cuối file này.

**Cảnh báo về fixture DOM:** như `payment_table.html` đã dạy — snapshot chỉ để viết XPath offline,
**số liệu trong đó là stale**, đừng lấy làm nguồn giá trị kỳ vọng.

---

## Bước 1 — Vá `TC_05` cho đúng vai trò

Hiện `TC_05` kết thúc bằng một cú click không assert gì ⇒ click hỏng cũng pass.

- Thêm `expect_submitted()` vào `BookingRequestPage`: assert đã rời `/private_offers/new`
  (match URL trang review lấy ở Bước 0).
- `confirm_booking_button = page.locator("//button[@type='submit']")` **quá rộng**: strict mode sẽ
  nổ nếu trang có nút submit thứ hai. Neo lại theo text tiếng Nhật của nút (lấy từ DOM Bước 0).
- File `tests/test_user_03_booking_request.py` thiếu newline cuối — thêm.

`TC_05` sau khi vá chỉ chịu trách nhiệm: điền form → submit → sang được trang review. Mọi assert
*nội dung* trang review thuộc về file test mới.

---

## Bước 2 — `pages/booking_confirm.py`

Class `BookingConfirmPage(page, base_url)`. Giữ nguyên quy ước hiện có: `goto_*` điều hướng /
`expect_*` assert / còn lại là action; **không action trong `__init__`**, chỉ khai báo locator lazy.

Nhóm locator dự kiến (tên thật điền sau Bước 0):

| Nhóm | Dùng để |
|---|---|
| `summary_datetime` | assert lại ngày/giờ slot — cross-check với `BookingSlot` |
| `summary_location`, `summary_genre` | assert lại những gì đã nhập ở trang trước |
| `payment_table` + `total_price` | assert tổng tiền khớp trang trước |
| `saved_card` / `card_form` (số thẻ, hạn, CVC, tên) | nhánh thẻ, chốt sau Bước 0 |
| `place_order_button` | nút xác nhận cuối |

Assertion chính — **không hardcode giá trị nào**:

- `expect_matches_draft(draft)` — so mọi trường với `BookingDraft` đóng băng ở trang trước (Bước 3).
  Đây là điểm giá trị nhất của cả test: hai trang render cùng một dữ liệu, lệch nhau là bug thật.
- `expect_total(expected: int)` — tái dùng đúng ý tưởng của `expect_payment_table_matches_selection`.
  Nếu markup bảng giá giống hệt trang `new`, **tách phần đọc bảng ra hàm dùng chung** thay vì
  copy `_parse_yen` + `sum_subtotal` sang file mới.

Nhánh thẻ (chọn **một** sau khi có DOM):

- *Đã lưu thẻ sẵn* → chỉ cần `expect_card_displayed()`, có thể phải chọn radio.
- *Input thường* → `fill_card(number, expiry, cvc)`, giá trị đọc từ env `TEST_CARD_NUMBER` /
  `TEST_CARD_EXPIRY` / `TEST_CARD_CVC`, và phải **đọc trong `conftest.py`** — `conftest` import
  `pages.*` trước `load_dotenv()`, nên `os.getenv` trong thân class sẽ không thấy `.env`.
  Tự thêm 3 biến này vào `.env` và `.env.example`.
- *Iframe cổng thanh toán* → `page.frame_locator(...)`; nhớ mỗi ô thẻ của Stripe là một iframe riêng.
  Không commit số thẻ thật — chỉ dùng số thẻ test của cổng.

---

## Bước 3 — Fixture: đóng băng dữ liệu kỳ vọng

Thêm vào `tests/conftest.py`, đều `scope="session"`:

```
booking_draft (frozen dataclass: slot, genre, location, options, total)
      ↓
submitted_booking   → đọc draft trên trang `new`, submit, trả về draft
      ↓
booking_confirm_page
```

- `booking_draft` phải đọc **ngay trước khi submit** (genre / địa điểm / option đang tick / tổng
  tiền) rồi mới bấm. Cùng pattern với `BookingSlot` và `ShootingOption`: test assert vào giá trị
  được trả về, không assert vào hằng số.
- `submitted_booking` là precondition duy nhất của file test mới ⇒ file đó chạy lẻ được, không phụ
  thuộc "file trước đã chạy chưa" (pytest chỉ giải thứ tự cho **fixture**, không cho test).
- `booking_confirm_page` **không** phụ thuộc `logged_in` — cùng lý do với `booking_request_page`:
  tới trang này bằng click, luôn sau khi đã đăng nhập.
- Va chạm cần nhớ: `TC_03`/`TC_04` toggle option. `booking_draft` đọc trạng thái *thật tại thời
  điểm đó*, không được giả định "không option nào đang tick".

---

## Bước 4 — `tests/test_user_04_booking_confirm.py`

`pytestmark = pytest.mark.incremental`. Tên file **phải** là `_04_` và là file cuối: collect theo
alphabet, và đây là file duy nhất thay đổi state không hồi lại được (tạo đơn thật).

| TC | Nội dung |
|---|---|
| `TC_01_confirm_page_is_displayed` | đúng URL trang review + các khối chính visible |
| `TC_02_summary_matches_booking_form` | `expect_matches_draft(draft)` — ngày/giờ, genre, địa điểm |
| `TC_03_payment_table_matches_booking_form` | tổng tiền + các dòng phí bằng đúng trang trước |
| `TC_04_card_section_is_displayed` | nhánh thẻ (nội dung tuỳ kết quả Bước 0) |
| `TC_05_place_order` | bấm nút cuối → assert trang hoàn tất (mã đơn / thông báo tiếng Nhật) |

Ẩn số cần chốt khi viết `TC_05`: sau khi đặt xong app hiện **mã đơn** hay chỉ một câu thông báo?
Nếu có mã, `print` nó ra để cleanup tay dễ tìm.

Mọi assert tiền/text do Vue render phải qua `expect()` (có retry). `.all()` và `inner_text()` không
auto-wait — bài học đã ghi trong `plan/payment-price-check.md`.

---

## Bước 5 — Verify & cập nhật doc

1. `.venv\Scripts\python.exe scripts\check.py` — không mở browser, bắt sai tên fixture + sai kiểu.
2. `pytest --collect-only -q` — xác nhận thứ tự file vẫn `01 → 02 → 03 → 04`.
3. Chạy cả suite ít nhất **3 lần** (trang mới, dễ flaky như `TC_01` đã từng).
4. Kiểm cả hướng phủ định: đổi một giá trị kỳ vọng thành sai, phải fail đúng dòng đó.
5. Pass rồi **mới** sửa `CLAUDE.md` (mục Layout + *Current state*) và `TODO.md` (đóng "Điền nốt form
   đặt lịch và submit", mở mục cleanup đơn).

---

## Hệ quả của việc đặt thật (đã chọn: cleanup tay)

- Mỗi run cả suite = **một đơn mới** trên staging cho photographer `PHOTOGRAPHER_NAME`.
- Slot vừa đặt sẽ **không còn `available`** ⇒ run sau `select_first_available_slot()` chọn ô khác.
  Đúng hành vi, nhưng calendar cạn dần; khi hết slot thì `goto_week_with_available_date()` bấm 次週
  tới `MAX_WEEKS = 10` rồi raise. Gặp lỗi đó thì đây là nguyên nhân, không phải bug code.
- Nếu form có field ghi chú/tin nhắn, nhét **một chuỗi nhận diện kèm timestamp** vào đó để lọc đơn
  do automation tạo khi dọn tay.
- Thêm một dòng `TODO.md`: "huỷ các đơn do automation tạo trên staging"; cân nhắc tự huỷ trong
  teardown nếu số đơn thành phiền.

---

## Ẩn số — điền sau Bước 0

- [ ] URL trang review: `________`
- [ ] URL trang hoàn tất: `________`
- [ ] Thẻ: đã lưu sẵn / input thường / iframe cổng nào: `________`
- [ ] Có bước xác nhận kép (modal) trước khi đặt không: `________`
- [ ] Bảng giá trang review có cùng markup `div.payment__table` không (quyết định tách code dùng
      chung hay không): `________`
- [ ] Text tiếng Nhật của nút xác nhận cuối: `________`

## Phụ thuộc đang hở ở trang trước

`select_filming_location()` hardcode `"Tokyo Tower"` và `expect_long_distance_fee_visible()` ngầm
giả định địa điểm đó phát sinh 遠方出張料. Vẫn là mục còn tồn trong `TODO.md`; không mở rộng trong
plan này, nhưng nếu staging đổi dữ liệu địa điểm thì `TC_05` hỏng **trước khi** tới được trang review.
