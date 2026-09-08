from playwright.sync_api import Page, expect


class PhotographerBookingPage:
    """Trang chi tiết photographer - phần calendar đặt lịch."""

    # Chỉ giữ path; host đến từ `base_url` (BASE_URL trong .env) để không hardcode
    # môi trường ở hai chỗ. "bebe" là photographer cố định trên staging - khi nào cần test nhiều photographer thì mới đổi thành tham số.
    PATH = "/photographers/bebe"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

        self.calendar = page.locator(
            "//div[@class='calendar']//table[@class='calendar__timeContainer']"
        )
       
        self.available_dates = self.calendar.locator("xpath=.//td[@class='available']")

    # --- điều hướng ---

    def goto_photographer_page(self):
        self.page.goto(f"{self.base_url}{self.PATH}")

    # --- hành động ---

    def select_available_date(self, index: int = 0):
        self.available_dates.nth(index).click()

    # --- kiểm tra (assertion) ---

    def expect_calendar_loaded(self):
        self.page.wait_for_load_state("networkidle")
        expect(self.calendar).to_be_visible()

    def expect_has_available_date(self):
        assert self.available_dates.count() > 0, "No available day in calendar"
