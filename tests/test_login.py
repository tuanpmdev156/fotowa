import os

import pytest
from playwright.sync_api import expect

INVALID_CREDENTIALS_ERROR = "メールアドレスまたはパスワードが正しくありません"

EMAIL = os.getenv("TEST_EMAIL")
PASSWORD = os.getenv("TEST_PASSWORD")

requires_account = pytest.mark.skipif(
    not (EMAIL and PASSWORD),
    reason="cần set TEST_EMAIL và TEST_PASSWORD để chạy các test yêu cầu tài khoản thật",
)


def test_login_form_is_displayed(login_page):
    login_page.goto_home_page()
    login_page.goto_login_page()
    login_page.expect_login_form_loaded()

@requires_account
def test_login_with_valid_credentials(login_page):
    login_page.login(EMAIL, PASSWORD)
    # TODO: thay bằng assertion trên trang thật sau khi đăng nhập, khi đã biết trang đó.


# def test_invalid_credentials_show_error(login_page):
#     login_page.goto()
#     login_page.login("not-a-real-user@example.com", "wrong-password")
#     login_page.expect_error(INVALID_CREDENTIALS_ERROR)
#     login_page.expect_still_on_login_page()


# def test_submit_with_empty_fields_stays_on_login_page(login_page):
#     login_page.goto()
#     login_page.submit()
#     login_page.expect_still_on_login_page()






