import { requireCredentials, test } from '../src/fixtures/test';

// Không cần credentials: test này chỉ xem form login có hiện ra không.
test('TC_01_login_form_is_displayed', async ({ loginPage, loggedOut }) => {
  void loggedOut;
  await loginPage.gotoHomePage();
  await loginPage.gotoLoginPage();
  await loginPage.expectLoginFormLoaded();
});

test('TC_02_login_with_valid_credentials', async ({ loginPage, loggedOut }) => {
  void loggedOut;
  // Lấy credentials trong thân test (không qua fixture) để thiếu `.env` thì skip chứ không fail.
  const credentials = requireCredentials();

  await loginPage.gotoHomePage();
  await loginPage.gotoLoginPage();
  await loginPage.expectLoginFormLoaded();
  await loginPage.login(credentials.email, credentials.password);
  await loginPage.expectLoginSuccess();
  await loginPage.expectLoggedIn();
});
