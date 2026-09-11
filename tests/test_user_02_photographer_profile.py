from pages.user.photographer_profile import PhotographerProfilePage


def TC_01_booking_calendar_is_displayed(photographer_profile_page: PhotographerProfilePage):
    photographer_profile_page.goto_profile_page()
    photographer_profile_page.expect_calendar_loaded()


def TC_02_booking_calendar_has_available_date(photographer_profile_page: PhotographerProfilePage):
    photographer_profile_page.goto_profile_page()
    photographer_profile_page.expect_has_available_date()
