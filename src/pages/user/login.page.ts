import { expect, type Locator, type Page } from '@playwright/test';

import { escapeRegExp } from '../../utils/format';

export class LoginPage {
  static readonly LOGIN_SUCCESS_MESSAGE = 'ログインに成功しました';

  readonly page: Page;
  readonly baseUrl: string;

  readonly loginLink: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly loggedInMarker: Locator;
  readonly loginSuccessMessage: Locator;

  // Constructor chỉ tạo locator (lazy), không thực hiện action nào —
  // một action ở đây sẽ đốt 30s timeout trên `about:blank` lúc fixture khởi tạo.
  constructor(page: Page, baseUrl: string) {
    this.page = page;
    this.baseUrl = baseUrl;
    this.loginLink = page.locator(
      "//a[contains(@class, 'signIn') and @href='/users/sign_in' and text()='ログイン']",
    );
    this.emailInput = page.locator("//input[@id='user_email']");
    this.passwordInput = page.locator("//input[@id='user_password']");
    this.loginButton = page.locator("//input[@type='submit' and @value='ログイン']");
    // Link logout(ログアウト) trong header — chỉ render khi đã đăng nhập
    this.loggedInMarker = page.locator("//a[@href='/users/sign_out' and @data-ga-label='sign-out']");
    this.loginSuccessMessage = page.locator(
      "//div[contains(@class,'globalNotice')]" +
        "/p[contains(@class,'globalNotice__description')]",
    );
  }

  // --- Navigation ---

  async gotoHomePage(): Promise<void> {
    await this.page.goto(this.baseUrl);
  }

  // --- Actions ---

  async fillEmail(email: string): Promise<void> {
    await this.emailInput.fill(email);
  }

  async fillPassword(password: string): Promise<void> {
    await this.passwordInput.fill(password);
  }

  async login(email: string, password: string): Promise<void> {
    await this.fillEmail(email);
    await this.fillPassword(password);
    await this.loginButton.click();
  }

  // --- Assertion ---

  async gotoLoginPage(): Promise<void> {
    await expect(this.loginLink).toBeVisible();
    await this.loginLink.click();
  }

  /** Kiểm tra trạng thái đã đăng nhập bằng cách tìm link logout(ログアウト) trong header. */
  async isLoggedIn(): Promise<boolean> {
    await this.page.waitForLoadState();
    // `count()` là phép thăm dò rẻ: chưa đăng nhập là kết quả bình thường, không được đốt 30s.
    return (await this.loggedInMarker.count()) > 0;
  }

  /** Assert đã đăng nhập. */
  async expectLoggedIn(): Promise<void> {
    // Marker khớp 2 node (header desktop + mobile) và bản desktop nằm trong dropdown hover,
    // nên kiểm tra "có trong DOM", không kiểm tra "nhìn thấy được".
    await expect(this.loggedInMarker.first()).toBeAttached();
  }

  /** Assert hành vi ngay sau khi đăng nhập: tự về home và hiện thông báo đăng nhập thành công. */
  async expectLoginSuccess(): Promise<void> {
    await expect(this.page).toHaveURL(new RegExp(`^${escapeRegExp(this.baseUrl)}/?$`));
    await expect(this.loginSuccessMessage).toBeVisible();
    await expect(this.loginSuccessMessage).toHaveText(LoginPage.LOGIN_SUCCESS_MESSAGE);
  }

  async expectLoginFormLoaded(): Promise<void> {
    await expect(this.emailInput).toBeVisible();
    await expect(this.passwordInput).toBeVisible();
    await expect(this.loginButton).toBeEnabled();
  }
}
