from pages.user.login import LoginPage


def TC_01_login_form_is_displayed(login_page: LoginPage, logged_out: None):
    login_page.goto_home_page()
    login_page.goto_login_page()
    login_page.expect_login_form_loaded()


def TC_02_login_with_valid_credentials(
    login_page: LoginPage, credentials: tuple[str, str], logged_out: None
):
    login_page.goto_home_page()
    login_page.goto_login_page()
    login_page.expect_login_form_loaded()
    login_page.login(*credentials)
    login_page.expect_login_success()
    login_page.expect_logged_in()
