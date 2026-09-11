import re

from playwright.sync_api import Page, expect


class LoginPage:

    LOGIN_SUCCESS_MESSAGE = "ログインに成功しました"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url
        self.login_link = page.locator("//a[contains(@class, 'signIn') and @href='/users/sign_in' and text()='ログイン']")
        self.email_input = page.locator("//input[@id='user_email']")
        self.password_input = page.locator("//input[@id='user_password']")
        self.login_button = page.locator("//input[@type='submit' and @value='ログイン']")
        # Link logout(ログアウト) trong header — chỉ render khi đã đăng nhập
        self.logged_in_marker = page.locator(
            "//a[@href='/users/sign_out' and @data-ga-label='sign-out']"
        )
        self.login_success_message = page.locator(
            "//div[contains(@class,'globalNotice')]"
            "/p[contains(@class,'globalNotice__description')]"
        )

    # --- Navigation ---

    def goto_home_page(self):
        self.page.goto(self.base_url)

    # --- Actions ---

    def fill_email(self, email: str):
        self.email_input.fill(email)

    def fill_password(self, password: str):
        self.password_input.fill(password)

    def login(self, email: str, password: str):
        self.fill_email(email)
        self.fill_password(password)
        self.login_button.click()

    # --- Assertion ---
    def goto_login_page(self):
        expect(self.login_link).to_be_visible()
        self.login_link.click()

    def is_logged_in(self) -> bool:
        """Kiểm tra trạng thái đã đăng nhập bằng cách tìm link logout(ログアウト) trong header."""
        self.page.wait_for_load_state()
        return self.logged_in_marker.count() > 0

    def expect_logged_in(self):
        """Assert đã đăng nhập."""
        expect(self.logged_in_marker.first).to_be_attached()

    def expect_login_success(self):
        """Assert hành vi ngay sau khi đăng nhập: tự về home và hiện thông báo đăng nhập thành công."""
        expect(self.page).to_have_url(re.compile(rf"^{re.escape(self.base_url)}/?$"))
        expect(self.login_success_message).to_be_visible()
        expect(self.login_success_message).to_have_text(self.LOGIN_SUCCESS_MESSAGE)

    def expect_login_form_loaded(self):
        expect(self.email_input).to_be_visible()
        expect(self.password_input).to_be_visible()
        expect(self.login_button).to_be_enabled()
