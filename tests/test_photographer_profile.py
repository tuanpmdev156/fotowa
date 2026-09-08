from pages.booking_request import BookingRequestPage
from pages.photographer_profile import PhotographerProfilePage


def test_01_calendar_is_displayed(photographer_profile_page: PhotographerProfilePage):
    photographer_profile_page.goto_profile_page()
    photographer_profile_page.expect_calendar_loaded()


def test_02_has_available_date(photographer_profile_page: PhotographerProfilePage):
    photographer_profile_page.expect_has_available_date()


def test_03_selected_slot_is_shown_on_booking_page(
    photographer_profile_page: PhotographerProfilePage,
    booking_request_page: BookingRequestPage,
):
    # Đọc ngày/giờ từ chính ô được bấm, nên không hardcode ngày nào cả.
    slot = photographer_profile_page.select_first_available_slot()
    booking_request_page.expect_slot(slot)
