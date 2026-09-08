from pages.login import LoginPage


def test_01_login_form_is_displayed(login_page: LoginPage):
    login_page.goto_home_page()
    login_page.goto_login_page()
    login_page.expect_login_form_loaded()


def test_02_login_with_valid_credentials(login_page: LoginPage, credentials: tuple[str, str]):
    login_page.login(*credentials)
    assert login_page.is_logged_in(), "Login failed: the header still shows the ログイン link"
