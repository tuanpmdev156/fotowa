# Verify bảng giá cuối trên `private_offers/new`

**Status (2026-09-10):** `pytest` cả suite **8/8 pass**, 3 run liên tiếp sau khi vá flaky
(xem *Flaky đã xử lý*). Trước đó flaky 1/4 run ở `TC_01_selected_slot_is_displayed`.

Ở `div.payment__table` verify **2 điểm**: (1) dòng option đã tick đúng **tên** + **giá**,
(2) `合計` bằng tổng các dòng phí đang hiển thị. **Không hardcode giá** — đọc từ
`div.shootingOptionControl` rồi assert vào bảng ⇒ cross-check hai nơi render cùng một dữ liệu.

## Đã làm

- **Tên file mang số vì pytest gom file theo alphabet**: `test_user_01_login.py` →
  `_02_photographer_profile` → `_03_booking_request`. Không đánh số thì booking chạy trước login,
  `TC_01_login_form_is_displayed` fail vì link ログイン đã biến mất.
- **Fixture `selected_slot`** (session, `tests/conftest.py`): goto profile → chờ calendar → tìm tuần
  có slot → bấm slot đầu. Chọn **một lần** cho cả session, mọi test booking assert trên cùng
  một `BookingSlot`.
- **`pages/booking_request.py`**:
  - `ShootingOption(label, price, selected)` — frozen dataclass, cùng kiểu `BookingSlot`.
  - `_parse_yen()` — control ghi `1,980円` (hậu tố), bảng ghi `¥1,980` (tiền tố) ⇒ so sánh qua số.
  - `read_option_cards()`, `sum_subtotal()` — locator thuần, không còn `evaluate_all`. Lọc dòng
    theo **class của `tr`** (`price`/`option_item`/`total`), không theo nhãn tiếng Nhật.
  - `set_option(label, selected=True)` — đọc `aria-pressed` trước nên không toggle ngược; click
    xong `expect(...).to_have_attribute()` chờ state đổi.
  - `expect_payment_table_loaded()` / `expect_options_loaded()` — gate render, dùng ở đầu TC_02.
  - `expect_payment_table_matches_selection()` — invariant gánh cả hai điểm verify.
- Bốn nhánh phủ định đã kiểm (lệch tổng, lệch nhãn, lệch giá, lệch số dòng) — đều fail đúng dòng.

## Bốn ẩn số đã chốt bằng chạy thật

| Ẩn số | Kết quả |
|---|---|
| `合計` cộng dòng nào | Mọi dòng đang hiển thị trừ `tr.total`. Đo: 24,200 → 48,400 → 50,380 |
| Toggle bằng gì | `input[type=checkbox]` không visible ⇒ phải click `label.shootingOptionControl__mainRow` |
| `撮影時間追加（+60分）` | Thêm dòng option, **không** đổi `撮影料金`; nhưng **đổi khoảng giờ** `09:00 - 10:00` → `09:00 - 11:00` |
| Bảng render hai lần? | Không, count = 1, không cần `.first` |

## Bẫy đã gặp

1. **`遠方出張料` là dòng có điều kiện**, chỉ render khi đã nhập địa điểm. Snapshot
   `fixtures/payment_table.html` có dòng này mà `合計` không cộng ⇒ ảnh chụp ở trạng thái khác,
   đừng lấy làm chuẩn số liệu.
2. **Tick `撮影時間追加（+60分）` đổi khoảng giờ** ⇒ `expect_available_slot()` sai nếu chạy sau khi
   tick. TC_01 chạy trước nên chưa ảnh hưởng — nhưng đừng đảo thứ tự test.
3. **Mọi assert tiền phải có retry.** Đọc bằng snapshot không retry: bỏ tick xong bảng vẫn còn 2
   dòng option và tổng 50,380, nhìn như bug app; assert lại bằng `expect()` thì pass — chỉ là đọc sớm.

## Flaky đã xử lý

**Triệu chứng:** 1/4 run cả suite, `TC_01_selected_slot_is_displayed` fail tại
`expect_available_slot()`. `expect_selected_slot_in_url()` ngay trước đó **pass** ⇒ đúng trang, URL
có đúng ngày/giờ slot; chỉ là `shootingDateTimeControl__details` chưa khớp text trong 5s default
timeout của `expect`. Chạy riêng file booking thì không tái hiện (4/4 pass).

**Nguyên nhân:** element do Vue render sau navigation, đôi khi chậm hơn 5s. Cùng một lớp lỗi với
`read_option_cards()`: `.all()` **không auto-wait**, nó chụp DOM ngay lúc gọi, nên card chưa render
là ra list rỗng.

**Vá:** thêm gate `expect(...).to_be_visible(timeout=15_000)` ở hai chỗ —
`expect_available_slot()` (trước hai assert text) và `read_option_cards()` (trước `.all()`).
Chỉ nới timeout cho bước *chờ xuất hiện*; các assert nội dung vẫn giữ 5s.
**Verify:** 3 run liên tiếp cả suite 8/8 pass. Chưa gặp lại, nhưng flaky 1/4 nên chưa gọi là chốt.

## Verify `遠方出張料` (phí di chuyển xa) — **đã làm, 9/9 pass (2026-09-11)**

**Kết quả:** cả suite 9/9 pass, 2 run. `TC_05_long_distance_fee_in_payment_table` chạy thật, không
`SKIPPED` (`pytest -rs` không có dòng skip) ⇒ locator cảnh báo `longDistanceFee` là thật, gate hoạt
động. Hướng âm: đổi nhãn thành `遠方出張料X` ⇒ fail đúng ở `booking_request.py:192`, không phải
skip. Bảng giá lúc đó: `撮影料金 ¥24,200 + 遠方出張料 ¥3,000 = 合計 ¥27,200` ⇒ phí nằm trong tổng.
Phần còn tồn (timeout của probe, import lặp, code chết, capture DOM cảnh báo) đã chuyển sang
`TODO.md`.

Kế hoạch gốc giữ lại bên dưới làm ghi chép.

**Phạm vi đã chốt:** phí đi xa **chỉ verify khi cảnh báo phí đi xa hiển thị**. Chọn địa điểm xong,
nếu form hiện cảnh báo (`long_distance_fee_warning`) thì bảng giá phải có dòng `遠方出張料` và tổng
phải cộng khoản đó; không hiện cảnh báo ⇒ địa điểm không phát sinh phí, `skip`, không fail. Không
làm nhánh âm (đổi qua lại giữa hai loại địa điểm), không tham số hoá tên địa điểm — để lại `TODO.md`.

**Vì sao phải gate bằng cảnh báo:** `遠方出張料` là dòng có điều kiện (mục *Bẫy đã gặp* 1) và
`"Tokyo Tower"` đang hardcode trong `select_filming_location()`. Nếu staging đổi dữ liệu địa điểm,
assert cứng sẽ fail vì dữ liệu chứ không phải vì bug.

### `pages/booking_request.py`

1. Import thêm `TimeoutError` của Playwright:
   ```python
   from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, expect
   ```
   **Không** thêm hằng cho nhãn `遠方出張料`: nó chỉ dùng trong đúng một hàm ⇒ inline thẳng, chấp
   nhận chuỗi lặp 2 chỗ (locator + message).
2. Giữ locator `long_distance_fee_warning` (`//div[contains(@class,'longDistanceFee')]`) làm **gate**,
   nhưng thay `expect_long_distance_fee_warning_visible()` bằng một probe rẻ — "không phát sinh phí"
   là kết quả hợp lệ nên không được dùng `expect()` (cùng lý do `is_logged_in()` dùng `count()` thay
   vì `expect`):
   ```python
   def has_long_distance_fee_warning(self, timeout: float = 5_000) -> bool:
       """Địa điểm vừa chọn có phát sinh phí đi xa không (theo cảnh báo trên form)."""
       try:
           self.long_distance_fee_warning.wait_for(state="visible", timeout=timeout)
       except PlaywrightTimeoutError:
           return False
       return True
   ```
   Khối cảnh báo chỉ render **một** element nên không cần `.first`.
   Cần `wait_for` chứ không phải `count()`: bảng giá và cảnh báo do Vue render bất đồng bộ sau khi
   chọn gợi ý địa điểm, probe ngay lập tức sẽ luôn ra `False`.
3. Thay `_get_option_price` bằng một helper đọc ô giá theo nhãn, dùng chung cho cả dòng option lẫn
   dòng phí:
   ```python
   def _price_cell(self, label: str) -> Locator:
       """Ô giá của dòng có `th` đúng bằng `label` trong bảng giá."""
       return self.payment_table.locator(
           f"//tbody/tr[th[normalize-space()='{label}']]/td[contains(@class,'privateOffers__price')]"
       )
   ```
   Hai chỗ gọi: `_price_cell(option.label)` trong `expect_payment_table_matches_selection()` và
   `_price_cell("遠方出張料")` trong `expect_long_distance_fee_charged()`.

   **Không lọc theo class của `tr`.** Nhãn trong bảng vốn duy nhất (`撮影料金`, `遠方出張料`,
   `オプション`, tên từng option, `合計`); trùng nhãn thì strict mode nổ chứ không im lặng chọn sai.
   Ràng buộc "dòng option phải là `tr.option_item`" không mất: ngay trên nó đã có
   `expect(self.option_rows).to_have_count(len(selected))`, mà `option_rows` lọc đúng
   `tr[@class='option_item']`. DOM nguồn: `fixtures/payment_table.html`.
4. Thêm assert cho dòng phí trong bảng giá:
   ```python
   def expect_long_distance_fee_charged(self) -> int:
       """Bảng giá có dòng 遠方出張料 với số tiền > 0. Trả về số tiền đọc được."""
       cell = self._price_cell("遠方出張料")
       expect(cell).to_be_visible()
       fee = _parse_yen(cell.inner_text())
       assert fee > 0, f"Có cảnh báo phí đi xa nhưng 遠方出張料 = ¥{fee}"
       return fee
   ```
   `expect(...).to_be_visible()` **trước** `inner_text()` là bắt buộc — `inner_text()` không
   auto-wait, cùng lớp lỗi với `.all()` ở mục *Bẫy đã gặp* 3 và *Flaky đã xử lý*.
   Đây mới là chỗ assert cứng: cảnh báo đã hiện thì dòng phí **phải** có.
5. Thêm newline cuối file.

### `tests/test_user_03_booking_request.py`

`TC_05` chỉ còn lo phí đi xa; bỏ cú `confirm_booking_button.click()` (click không assert thì hỏng
cũng pass, lại đẩy trang sang review làm bẩn state — để dành cho TC submit khi làm
`plan/booking-confirm-payment.md`). Lưu ý file test đang gọi tên cũ
`expect_long_distance_fee_visible()` (page object đã đổi thành `..._warning_visible`) ⇒ hiện chạy là
`AttributeError`; sửa luôn.

```python
def TC_05_long_distance_fee_in_payment_table(booking_request_page: BookingRequestPage):
    """Địa điểm có cảnh báo phí đi xa: bảng giá hiện dòng 遠方出張料 và tổng có cộng khoản đó."""
    booking_request_page.select_first_genre()
    booking_request_page.select_filming_location()
    if not booking_request_page.has_long_distance_fee_warning():
        pytest.skip("Địa điểm đã chọn không phát sinh 遠方出張料")
    booking_request_page.expect_long_distance_fee_charged()
    booking_request_page.expect_payment_table_matches_selection()
```

Phần "tính đúng vào tổng" do `expect_payment_table_matches_selection()` gánh: nó đã assert
`total == sum_subtotal()`, mà `sum_subtotal()` cộng **mọi** dòng không phải `total` ⇒ dòng phí đi xa
bắt buộc phải nằm trong tổng. Không giả định `撮影料金` đứng yên khi đổi địa điểm — an toàn hơn cách
so delta `tổng_sau == tổng_trước + phí`.

`pytest.skip` ở giữa module có `pytestmark = incremental` là an toàn: hook
`pytest_runtest_makereport` trong `tests/conftest.py` lọc `Skipped` nên không arm cờ, test sau không
bị skip lây. Vào `TC_05` thì `TC_04` đã bỏ tick hết option, bảng chỉ còn `撮影料金` + phí đi xa.
Thêm newline cuối file.

### Verify

1. `.venv\Scripts\python.exe scripts\check.py` — fixture + pyright, không mở browser.
2. `.venv\Scripts\python.exe -m pytest tests/test_user_03_booking_request.py` — chạy **2–3 lần**
   (bảng giá do Vue render, đã flaky một lần).
3. **`TC_05` phải chạy thật, không được `skip`.** Rủi ro lớn nhất của kiểu gate này: class
   `longDistanceFee` chưa verify được bằng fixture nào (`grep -rni longdistance` chỉ trúng đúng dòng
   khai báo), nếu sai tên thì probe luôn trả `False` và test **skip mãi mãi mà vẫn xanh**. Với
   `"Tokyo Tower"` (địa điểm chắc chắn phát sinh phí) mà thấy `SKIPPED` thì đó là locator sai, không
   phải dữ liệu. Chạy `pytest -rs` để thấy rõ dòng skip.
4. Capture DOM khối cảnh báo lưu vào `fixtures/` (ví dụ `fixtures/long_distance_fee_warning.html`)
   để lần sau viết XPath offline được, như các fixture khác.
5. Hướng âm: tạm đổi nhãn trong `self._price_cell("遠方出張料")` thành `"遠方出張料X"`,
   phải fail đúng ở `expect_long_distance_fee_charged` (không phải skip), rồi revert.

### Pass rồi mới sửa doc

- `TODO.md`: đóng mục `遠方出張料`, giữ lại một mục nhỏ cho hai việc chưa làm (hardcode
  `"Tokyo Tower"`, nhánh âm đổi qua địa điểm không phát sinh phí).
- `CLAUDE.md`: cập nhật *Current state*, và sửa tên file sai ở mục Layout —
  `plan/payment-price-check.md` → `plan/booking-price-check.md`.

## Còn tồn

- [x] `遠方出張料` — xong, xem mục trên. Phần dọn dẹp còn lại nằm trong `TODO.md`.
- [ ] Điền nốt form + submit: sau genre còn `spotControl`, `discountCodeControl`.
      Trang review + thanh toán có plan riêng ở `plan/booking-confirm-payment.md`.
- [ ] Chưa có test nhánh **tick option rồi đổi slot** — khoảng giờ do `撮影時間追加` sửa có reset đúng không.
