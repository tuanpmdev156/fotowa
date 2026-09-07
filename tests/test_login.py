import os

import pytest
from playwright.sync_api import expect

INVALID_CREDENTIALS_ERROR = "メールアドレスまたはパスワードが正しくありません"

EMAIL = os.getenv("TEST_EMAIL")
PASSWORD = os.getenv("TEST_PASSWORD")

requires_account = pytest.mark.skipif(
    not (EMAIL and PASSWORD),
    reason="set TEST_EMAIL and TEST_PASSWORD to run tests that need a real account",
)


def test_login_form_is_displayed(login_page):
    login_page.goto()
    login_page.expect_loaded()


def test_submit_with_empty_fields_stays_on_login_page(login_page):
    login_page.goto()
    login_page.submit()
    login_page.expect_still_on_login_page()


def test_invalid_credentials_show_error(login_page):
    login_page.goto()
    login_page.login("not-a-real-user@example.com", "wrong-password")
    login_page.expect_error(INVALID_CREDENTIALS_ERROR)
    login_page.expect_still_on_login_page()


@requires_account
def test_valid_credentials_leave_login_page(login_page, page, login_url):
    login_page.goto()
    login_page.login(EMAIL, PASSWORD)
    # TODO: swap for an assertion on the real post-login page once it is known.
    expect(page).not_to_have_url(login_url)
