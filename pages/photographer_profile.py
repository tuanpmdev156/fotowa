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
    """
    Trang chi tiết photographer
    """

    # Calendar chỉ hiện 7 ngày.
    # Khi kín lịch bấm 次週 để tìm lịch trống, tối đa MAX_WEEKS lần,nếu vẫn kín lịch sau đó thì fail.
    
    MAX_WEEKS = 10

    def __init__(self, page: Page, base_url: str, photographer_path: str):
        self.page = page
        self.base_url = base_url
        self.photographer_path = photographer_path

        self.calendar = page.locator(
            "//div[@class='calendar']//table[@class='calendar__timeContainer']"
        )
        self.next_week_link = page.locator("//li[@class='next']/a[text()='次週']")

        self.booking_table_header = page.locator("//table[@class='calendar__header']")
        # Table cho mỗi tuần (7 cột, 24 hàng).
        self.booking_table = self.calendar.locator("xpath=.//table[@class='events']")
        self.current_year_moth = self.booking_table_header.locator("xpath=.//tr[@class='month']/th[@colspan]")
        # Cột ngày
        self.day_headers = self.booking_table_header.locator("xpath=.//tr[@class='dayname']/td")
         # Cột giờ
        self.time_slots = self.calendar.locator("xpath=.//table[@class='time']//td")
        self.available_dates = self.calendar.locator("xpath=.//td[@class='available']")

        

    # --- Navigation ---

    def goto_profile_page(self):
        self.page.goto(f"{self.base_url}{self.photographer_path}")

    # Javascript function kiểm tra ngày đầu tiên trong tuần đã thay đổi hay chưa, so với giá trị cũ.
    _FIRST_DAY_CHANGED = """old =>
        (document.querySelector("table.calendar__header tr.dayname td")
            ?.innerText.trim() ?? old) !== old"""

    def goto_next_week(self):
        """Bấm next và chờ calendar render xong tuần mới."""
        first_day_in_week = self.day_headers.first.inner_text().strip()
        self.next_week_link.click()
        self.page.wait_for_function(self._FIRST_DAY_CHANGED, arg=first_day_in_week)

    def goto_week_with_available_date(self):
        """Bấm sang tuần kế tiếp cho tới khi calendar có ít nhất một slot trống.
        Nếu sau MAX_WEEKS lần bấm vẫn không có slot trống thì fail.
        """
        for clicked in range(self.MAX_WEEKS + 1):
            if self.available_dates.count() > 0:
                return
            if clicked < self.MAX_WEEKS:
                self.goto_next_week()

        raise AssertionError(
            f"No available slot after clicking {self.MAX_WEEKS} week times"
        )

    # --- Actions ---

    def select_first_available_slot(self) -> BookingSlot:
        """Click slot trống đầu tiên, trả về ngày/giờ của chính ô đó."""
        for column in range(self.booking_table.count()):
            cells = self.booking_table.nth(column).locator("xpath=.//tr/td")
            # Lấy class của cả cột trong một lần gọi thay vì hỏi từng ô.
            classes: list[str] = cells.evaluate_all("els => els.map(e => e.className)")
            for row, css in enumerate(classes):
                if "available" in css.split():
                    slot = self._read_slot(column, row)
                    cells.nth(row).click()
                    return slot

        raise AssertionError("No available slot in the calendar")

    # --- Private Methods ---

    def _read_slot(self, column: int, row: int) -> BookingSlot:
        year, month = self._read_year_month(column)
        day = self.day_headers.nth(column).locator("xpath=./span").inner_text()
        return BookingSlot(
            year=year,
            month=month,
            day=int(day.strip()),
            time=self.time_slots.nth(row).inner_text().strip(),
        )

    def _read_year_month(self, column: int) -> tuple[int, int]:
        """Năm/tháng của tuầnđang hiển thị.
        """
        cells: list[tuple[int, str]] = self.current_year_moth.evaluate_all(
            "els => els.map(e => [e.colSpan, e.innerText.trim()])"
        )
        cursor = 0
        for span, text in cells:
            cursor += span
            if column < cursor:
                year, month = text.split("/")
                return int(year), int(month)

        raise AssertionError(f"Column {column} is outside the booking calendar")

    # --- Assertion ---

    def expect_calendar_loaded(self):
        expect(self.calendar).to_be_visible()

    def expect_has_available_date(self):
        # Tìm tuần có slot trống trước, rồi mới assert
        self.goto_week_with_available_date()
        expect(self.available_dates).not_to_have_count(0)
