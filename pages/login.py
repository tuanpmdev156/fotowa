from playwright.sync_api import Page, expect

class LoginPage:

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url
        self.login_link = page.locator("//a[contains(@class, 'signIn') and @href='/users/sign_in' and text()='ログイン']")
        self.email_input = page.locator("//input[@id='user_email']")
        self.password_input = page.locator("//input[@id='user_password']")
        self.login_button = page.locator("//input[@type='submit' and @value='ログイン']")
        self.error_message = page.locator("//ul[@class='errorMessage']/li[contains(text(),'メールアドレスまたはパスワードが正しくありません')]")

    # --- điều hướng ---

    def goto_home_page(self):
        self.page.goto(self.base_url)

    # --- hành động ---

    def fill_email(self, email: str):
        self.email_input.fill(email)

    def fill_password(self, password: str):
        self.password_input.fill(password)        

    def login(self, email: str, password: str):
        self.fill_email(email)
        self.fill_password(password)
        self.login_button.click()

    # --- kiểm tra (assertion) ---
    def goto_login_page(self):
        expect(self.login_link).to_be_visible()
        self.login_link.click()

    def is_logged_in(self) -> bool:
        self.page.wait_for_load_state()
        return not self.login_link.is_visible()

    def expect_login_form_loaded(self):
        expect(self.email_input).to_be_visible()
        expect(self.password_input).to_be_visible()
        expect(self.login_button).to_be_enabled()

    # def expect_error(self, message: str):
    #     expect(self.error_message).to_be_visible()
    #     expect(self.error_message).to_contain_text(message)