from pages.photographer_profile import PhotographerProfilePage


def test_calendar_is_displayed(photographer_profile_page: PhotographerProfilePage):
    photographer_profile_page.goto_profile_page()
    photographer_profile_page.expect_calendar_loaded()
    photographer_profile_page.expect_has_available_date()
