from datetime import datetime, timedelta

from playwright.sync_api import Page, expect

from pages.photographer_profile import BookingSlot

# Một buổi chụp mặc định dài 1 tiếng, nên trang đích hiển thị
# "giờ đã chọn - giờ đã chọn + 1h"
SHOOTING_DURATION = timedelta(hours=1)


def _plus_one_hour(hhmm: str) -> str:
    return (datetime.strptime(hhmm, "%H:%M") + SHOOTING_DURATION).strftime("%H:%M")


class BookingRequestPage:
    """
    Trang đích sau khi chọn một ô trống trên booking calendar.
    """

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

        self.selected_datetime = page.locator("//div[@id='app']//div[@class='shootingDateTimeControl__details']")

    # --- kiểm tra (assertion) ---
    
    def expect_slot(self, slot: BookingSlot):
        """Assert hiển thị đúng ngày/giờ vừa bấm ở calendar."""
        expect(self.selected_datetime).to_contain_text(
            f"{slot.year}/{slot.month:02d}/{slot.day:02d}"
        )
        expect(self.selected_datetime).to_contain_text(
            f"{slot.time} - {_plus_one_hour(slot.time)}"
        )
