from playwright.sync_api import Page, expect

from pages.photographer_profile import BookingSlot


class BookingRequestPage:
    """Trang đích sau khi chọn một ô trống trên calendar.

    Không có `PATH`: path là dynamic và ta luôn tới đây bằng click, không bằng
    `goto`. Nếu cần assert URL thì dùng regex, vd:
        expect(self.page).to_have_url(re.compile(r"/reservations/"))

    TODO: locator dưới đây là placeholder - thay bằng XPath thật từ DevTools.
    """

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

        # TODO: thay bằng XPath thật của chỗ hiển thị ngày/giờ đã chọn.
        self.selected_datetime = page.locator("//*[contains(@class,'selectedDateTime')]")

    # --- kiểm tra (assertion) ---

    def expect_slot(self, slot: BookingSlot):
        """Assert trang đích hiển thị đúng ngày/giờ vừa bấm ở calendar."""
        # TODO: khớp format thật của trang đích. Đang giả định kiểu Nhật
        # "2026年9月10日" và giờ "09:00" nằm trong cùng một element.
        expect(self.selected_datetime).to_contain_text(
            f"{slot.year}年{slot.month}月{slot.day}日"
        )
        expect(self.selected_datetime).to_contain_text(slot.time)
