import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from playwright.sync_api import Locator, Page, expect

from pages.photographer_profile import BookingSlot

# Một buổi chụp mặc định dài 1 tiếng, nên trang đích hiển thị "giờ đã chọn - giờ đã chọn + 1h"
SHOOTING_DURATION = timedelta(hours=1)


def _plus_one_hour(hhmm: str) -> str:
    return (datetime.strptime(hhmm, "%H:%M") + SHOOTING_DURATION).strftime("%H:%M")


def _parse_yen(text: str) -> int:
    """Đổi text tiền thành số. Ví dụ:
    - `1,980円` (hậu tố)
    - `¥1,980` (tiền tố)
    """
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        raise AssertionError(f"Couldn't read price from {text!r}")
    return int(digits)


@dataclass(frozen=True)
class ShootingOption:
    label: str
    price: int
    selected: bool


class BookingRequestPage:
    """Trang đích sau khi chọn một slot trống trên booking calendar.
    """

    def __init__(self, page: Page, base_url: str, photographer_path: str):
        self.page = page
        self.base_url = base_url
        self.path_pattern = rf"{re.escape(photographer_path)}/private_offers/new"

        self.selected_datetime = page.locator("//div[@id='app']//div[@class='shootingDateTimeControl__details']")

        # self.genre_button = page.locator("#private_offer_creation_form_genre_id")

        # self.genre_options = page.locator(
        #     'div.genreOption[data-genre-id]:not([data-genre-id=""]):visible'
        # )

        self.option_cards = page.locator("//div[contains(@class,'shootingOptionControl__card')]")

        self.payment_table = page.locator("//div[@class='payment__table']")
        # Mọi ô giá trừ dòng Total(合計).
        self.subtotal_prices = self.payment_table.locator(
            "//tbody/tr[not(@class='total')]/td[contains(@class,'privateOffers__price')]"
        )
        # Các option đang tick.
        self.option_rows = self.payment_table.locator("//tbody/tr[@class='option_item']")
        self.total_price = self.payment_table.locator("//tr[@class='total']//td[@class='privateOffers__price']")

    # --- Actions ---

    # def select_first_genre(self):
    #     """Chọn ジャンル đầu tiên. Bắt buộc: khối option chưa render khi chưa chọn genre."""
    #     self.genre_button.click()
    #     self.genre_options.first.click()
    #     expect(self.option_cards.first).to_be_visible()

    def set_option(self, label: str, selected: bool = True):
        """Đưa option về trạng thái `selected`. Nếu đã đúng trạng thái thì không bấm nữa."""
        card = self._option_card(label)
        if (card.get_attribute("aria-pressed") == "true") == selected:
            return
        card.locator("//label[contains(@class,'shootingOptionControl__mainRow')]").click()
        expect(card).to_have_attribute("aria-pressed", "true" if selected else "false")

    # --- Readers ---

    def read_option_cards(self) -> list[ShootingOption]:
        """Đọc tên/giá/trạng thái của từng option card.
        """
        cards = self.option_cards.all()
        if not cards:
            raise AssertionError("No shooting option cards found on the page.")
        return [
            ShootingOption(
                label = card.locator(
                    "//p[contains(@class,'shootingOptionControl__title')]"
                    "//span[contains(@class,'typographyBold')]"
                ).inner_text(),
                price = _parse_yen(
                    card.locator("//p[contains(@class,'shootingOptionControl__price')]").inner_text()
                ),
                selected = card.get_attribute("aria-pressed") == "true",
            )
            for card in cards
        ]

    def sum_subtotal(self) -> int:
        """Cộng mọi dòng trong bảng giá, trừ dòng Total(合計). Bỏ qua dòng không có giá."""
        return sum(_parse_yen(text) for text in self.subtotal_prices.all_inner_texts() if text.strip())

    # --- Private Methods ---

    def _option_card(self, label: str) -> Locator:
        return self.option_cards.filter(
            has=self.page.locator(".shootingOptionControl__title span", has_text=label)
        )

    def _get_option_price(self, label: str) -> Locator:
        """Giá của dòng option đang tick."""
        return self.payment_table.locator(
            f"//tr[contains(@class,'option_item')][th[normalize-space()='{label}']]"
            "/td[contains(@class,'privateOffers__price')]"
        )

    # --- Assertion ---

    def expect_selected_slot_in_url(self, slot: BookingSlot):
        """Assert đã sang trang tạo private offer, đúng ngày/giờ của ô vừa bấm.

        URL contains(`?shooting_date=2026-09-12&shooting_time=18:30`)
        """
        expect(self.page).to_have_url(
            re.compile(
                rf"^{re.escape(self.base_url)}{self.path_pattern}"
                rf"\?shooting_date={slot.year}-{slot.month:02d}-{slot.day:02d}"
                rf"&shooting_time={slot.time}"
            )
        )

    def expect_available_slot(self, slot: BookingSlot):
        """Assert hiển thị đúng ngày/giờ vừa bấm ở calendar."""
        expect(self.selected_datetime).to_contain_text(
            f"{slot.year}/{slot.month:02d}/{slot.day:02d}"
        )
        expect(self.selected_datetime).to_contain_text(
            f"{slot.time} - {_plus_one_hour(slot.time)}"
        )

    def expect_payment_table_loaded(self):
        expect(self.payment_table).to_be_visible()

    def expect_options_loaded(self):
        expect(self.option_cards.first).to_be_visible()

    def expect_no_option_selected(self):
        """Mặc định trang không tick sẵn option nào."""
        assert [o.label for o in self.read_option_cards() if o.selected] == []
        expect(self.option_rows).to_have_count(0)

    def expect_total(self, expected: int):
        expect(self.total_price).to_have_text(f"¥{expected:,}")

    def expect_payment_table_matches_selection(self):
        """Bảng giá khớp đúng những option đang tick — cả tên, giá và tổng.
        """
        selected = [opt for opt in self.read_option_cards() if opt.selected]

        # 1. Bảng có đúng số lượng option đang tick, mỗi dòng đúng cặp tên và giá.
        expect(self.option_rows).to_have_count(len(selected))
        for option in selected:
            expect(self._get_option_price(option.label)).to_have_text(f"¥{option.price:,}")

        # 2. Tổng bằng đúng các dòng đang hiển thị.
        self.expect_total(self.sum_subtotal())
