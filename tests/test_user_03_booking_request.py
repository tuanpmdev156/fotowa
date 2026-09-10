import pytest

from pages.booking_request import BookingRequestPage
from pages.photographer_profile import BookingSlot

# Các test dùng chung một tab và chạy theo thứ tự khai báo: test sau bị skip nếu test trước fail.
pytestmark = pytest.mark.incremental


def TC_01_selected_slot_is_displayed(
    booking_request_page: BookingRequestPage, selected_slot: BookingSlot
):
    # Assert URL trước: sai trang thì fail ngay ở đây thay vì chờ hết timeout của element.
    booking_request_page.expect_selected_slot_in_url(selected_slot)
    booking_request_page.expect_available_slot(selected_slot)


def TC_02_payment_table_has_no_option_by_default(booking_request_page: BookingRequestPage):
    """Chưa tick option nào."""
    #booking_request_page.select_first_genre()
    booking_request_page.expect_payment_table_loaded()
    booking_request_page.expect_options_loaded()
    booking_request_page.expect_no_option_selected()
    booking_request_page.expect_payment_table_matches_selection()


def TC_03_selected_option_in_payment_table(booking_request_page: BookingRequestPage):
    """Từng option: tick thì bảng hiện đúng tên option + giá và cộng vào tổng, bỏ tick thì trừ lại."""
    for option in booking_request_page.read_option_cards():
        booking_request_page.set_option(option.label, selected=True)
        booking_request_page.expect_payment_table_matches_selection()

        booking_request_page.set_option(option.label, selected=False)
        booking_request_page.expect_payment_table_matches_selection()


def TC_04_payment_table_sums_all_options(booking_request_page: BookingRequestPage):
    """Tick cả hai option: đủ hai dòng và tổng cộng đủ cả hai."""
    options = booking_request_page.read_option_cards()
    for option in options:
        booking_request_page.set_option(option.label)

    booking_request_page.expect_payment_table_matches_selection()

    # Bỏ tick hết: vừa trả trang về trạng thái sạch cho test sau, vừa assert app có trừ lại.
    for option in booking_request_page.read_option_cards():
        booking_request_page.set_option(option.label, selected=False)
    booking_request_page.expect_no_option_selected()
    booking_request_page.expect_payment_table_matches_selection()
