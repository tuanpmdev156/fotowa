from playwright.sync_api import Page, expect

class LoginPage:

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url
        self.email_input = page.get_by_role("textbox", name="メールアドレス")
        self.password_input = page.get_by_role("textbox", name="パスワード")
        self.submit_button = page.get_by_role("button", name="ログイン")
        self.error_message = page.get_by_text("メールアドレスまたはパスワードが正しくありません")

    # --- navigation ---

    def goto(self):
        self.page.goto(self.base_url)

    # --- actions ---

    def fill_email(self, email: str):
        self.email_input.fill(email)

    def fill_password(self, password: str):
        self.password_input.fill(password)

    def submit(self):
        self.submit_button.click()

    def login(self, email: str, password: str):
        self.fill_email(email)
        self.fill_password(password)
        self.submit()

    # --- assertions ---

    def expect_loaded(self):
        expect(self.email_input).to_be_visible()
        expect(self.password_input).to_be_visible()
        expect(self.submit_button).to_be_enabled()

    def expect_error(self, message: str):
        expect(self.error_message).to_be_visible()
        expect(self.error_message).to_contain_text(message)

    def expect_still_on_login_page(self):
        expect(self.page).to_have_url(self.base_url)
