from dataclasses import dataclass

from playwright.sync_api import Page, expect


@dataclass(frozen=True)
class BookingSlot:
    """Ngày/giờ của ô calendar vừa được chọn.
    """

    year: int
    month: int
    day: int
    time: str  # "HH:MM"


class PhotographerProfilePage:
    """Trang chi tiết photographer - phần calendar đặt lịch.

    Calendar không lưu ngày/giờ trong `td`: ô `available` chỉ chứa icon. Ngày/giờ
    suy ra từ vị trí:
      - giờ  = index hàng của ô  -> tra `table.time` ở cùng index
      - ngày = ô thuộc `table.events` thứ mấy (0-6) -> tra `tr.dayname` ở cùng index
      - năm/tháng = `tr.month` trong `table.calendar__header` ("2026/09")
    """

    # "bebe" là photographer cố định trên staging - khi nào cần test nhiều photographer thì mới đổi thành tham số.
    PATH = "/photographers/bebe"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

        self.calendar = page.locator(
            "//div[@class='calendar']//table[@class='calendar__timeContainer']"
        )

        self.available_dates = self.calendar.locator("xpath=.//td[@class='available']")

        # Một `table.events` cho mỗi ngày (7 cột), mỗi bảng 24 hàng.
        self.day_tables = self.calendar.locator("xpath=.//table[@class='events']")
        # Cột giờ bên trái, cùng số hàng với mỗi `table.events`.
        self.time_slots = self.calendar.locator("xpath=.//table[@class='time']//td")

        self.header = page.locator("//table[@class='calendar__header']")
        self.year_month = self.header.locator("xpath=.//tr[@class='month']/th[@colspan]")
        self.day_headers = self.header.locator("xpath=.//tr[@class='dayname']/td")

    # --- điều hướng ---

    def goto_profile_page(self):
        self.page.goto(f"{self.base_url}{self.PATH}")

    # --- hành động ---

    def select_first_available_slot(self) -> BookingSlot:
        """Click ô trống đầu tiên, trả về ngày/giờ của chính ô đó."""
        for column in range(self.day_tables.count()):
            cells = self.day_tables.nth(column).locator("xpath=.//tr/td")
            # Lấy class của cả cột trong một lần gọi thay vì hỏi từng ô.
            classes: list[str] = cells.evaluate_all("els => els.map(e => e.className)")
            for row, css in enumerate(classes):
                if "available" in css.split():
                    slot = self._read_slot(column, row)
                    cells.nth(row).click()
                    return slot

        raise AssertionError("No available slot in the calendar")

    # --- đọc dữ liệu ---

    def _read_slot(self, column: int, row: int) -> BookingSlot:
        year, month = self._read_year_month()
        day = self.day_headers.nth(column).locator("xpath=./span").inner_text()
        return BookingSlot(
            year=year,
            month=month,
            day=int(day.strip()),
            time=self.time_slots.nth(row).inner_text().strip(),
        )

    def _read_year_month(self) -> tuple[int, int]:
        # `<th colspan="7"><span>2026</span>/09</th>` -> "2026/09"
        year, month = self.year_month.inner_text().strip().split("/")
        return int(year), int(month)

    # --- kiểm tra (assertion) ---

    def expect_calendar_loaded(self):
        # `expect` tự retry tới DEFAULT_TIMEOUT_MS, không cần chờ load state.
        expect(self.calendar).to_be_visible()

    def expect_has_available_date(self):
        # `not_to_have_count(0)` retry tới DEFAULT_TIMEOUT_MS
        expect(self.available_dates).not_to_have_count(0)
