import pytest

from pages.booking_request import BookingRequestPage
from pages.photographer_profile import PhotographerProfilePage

# Các test dùng chung một tab và chạy theo thứ tự khai báo: test sau bị skip nếu test trước fail.
pytestmark = pytest.mark.incremental


def test_01_booking_calendar_is_displayed(photographer_profile_page: PhotographerProfilePage):
    photographer_profile_page.goto_profile_page()
    photographer_profile_page.expect_calendar_loaded()


def test_02_has_available_date(photographer_profile_page: PhotographerProfilePage):
    photographer_profile_page.expect_has_available_date()


def test_03_select_first_available_slot(
    photographer_profile_page: PhotographerProfilePage,
    booking_request_page: BookingRequestPage,
):
    # Đọc ngày/giờ từ ô được chọn
    slot = photographer_profile_page.select_first_available_slot()
    booking_request_page.expect_slot(slot)
