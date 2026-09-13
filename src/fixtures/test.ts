/**
 * Fixture dùng chung cho cả bộ test.
 *
 * Sơ đồ phụ thuộc (scope trong ngoặc):
 *
 *     context (worker) ─→ page (test) ─→ loginPage ─→ loggedIn ─→ photographerProfilePage
 *         │                  │                                        │
 *         │                  └─→ loggedOut (chỉ test form login)      └─→ selectedSlot
 *         │
 *         └─→ availableSlot (worker, tự mở/đóng tab scratch, chỉ trả dữ liệu)
 *
 * Luật scope: fixture worker-scope không xin được fixture test-scope, nên hễ fixture nào giữ
 * `page` thì buộc phải là test-scope. Tương đương luật session/function của pytest.
 */

import * as fs from 'node:fs';

import { test as base, chromium, expect, type BrowserContext } from '@playwright/test';

import * as env from '../config/env';
import type { Credentials } from '../config/env';
import { BookingRequestPage } from '../pages/user/booking-request.page';
import { LoginPage } from '../pages/user/login.page';
import {
  PhotographerProfilePage,
  type BookingSlot,
} from '../pages/user/photographer-profile.page';

// Cookie session của app fotowa (Rails), khác với cookie cổng SSO `AWSELBAuthSessionCookie-*`.
const APP_SESSION_COOKIE = '_session_id';

interface WorkerFixtures {
  persistentContext: BrowserContext;
  appBaseUrl: string;
  appPhotographerPath: string;
  workerCredentials: Credentials;
  availableSlot: BookingSlot;
}

interface TestFixtures {
  loginPage: LoginPage;
  loggedIn: void;
  loggedOut: void;
  photographerProfilePage: PhotographerProfilePage;
  bookingRequestPage: BookingRequestPage;
  selectedSlot: BookingSlot;
}

/**
 * Đăng nhập app fotowa; đã đăng nhập rồi thì không làm lại.
 *
 * Là hàm thường chứ không phải fixture, để fixture ở scope nào cũng gọi được —
 * cookie nằm ở `context` dùng chung nên đăng nhập trên tab nào thì mọi tab đều thấy.
 */
export async function signIn(loginPage: LoginPage, credentials: Credentials): Promise<void> {
  await loginPage.gotoHomePage();
  if (await loginPage.isLoggedIn()) {
    return;
  }

  await loginPage.gotoLoginPage();
  await loginPage.expectLoginFormLoaded();
  await loginPage.login(credentials.email, credentials.password);
  await loginPage.expectLoggedIn();
}

/** Mở profile, tìm tuần có lịch trống, bấm ô trống đầu tiên. Trả về ngày/giờ của chính ô đó. */
async function findFirstAvailableSlot(profile: PhotographerProfilePage): Promise<BookingSlot> {
  await profile.gotoProfilePage();
  await profile.expectCalendarLoaded();
  await profile.gotoWeekWithAvailableDate();
  return profile.selectFirstAvailableSlot();
}

export const test = base.extend<TestFixtures, WorkerFixtures>({
  // ------------------------------------------------------------------------------------
  // Cấu hình đọc từ `.env` (worker scope)
  // ------------------------------------------------------------------------------------

  appBaseUrl: [
    async ({}, use) => {
      await use(env.baseUrl());
    },
    { scope: 'worker' },
  ],

  appPhotographerPath: [
    async ({}, use) => {
      await use(env.photographerPath());
    },
    { scope: 'worker' },
  ],

  // Playwright không có kiểu skip lan truyền như `pytest.skip()` trong fixture, và worker fixture
  // thì không skip được. Test nào cần credentials phải tự gọi `skipWithoutCredentials()`.
  workerCredentials: [
    async ({}, use) => {
      const credentials = env.credentials();
      if (credentials === null) {
        throw new Error('Must set TEST_EMAIL and TEST_PASSWORD in `.env`');
      }
      await use(credentials);
    },
    { scope: 'worker' },
  ],

  // ------------------------------------------------------------------------------------
  // Browser, context và tab
  // ------------------------------------------------------------------------------------

  persistentContext: [
    async ({}, use) => {
      // Mở lại profile cũ, không tạo context mới, để giữ cache của Chrome
      // (vendor.js 10.5MB không nén: cache nguội ⇒ DOMContentLoaded ~110s).
      fs.mkdirSync(env.profileDir(), { recursive: true });
      const context = await chromium.launchPersistentContext(env.profileDir(), {
        channel: 'chrome',
        headless: false,
      });
      await use(context);
      await context.close();
    },
    { scope: 'worker' },
  ],

  // Ghi đè `context` gốc để tiêm context đã qua cổng SSO vào.
  // Vì fixture là lazy, ghi đè `context` khiến `browser`/`browserName` không bao giờ được khởi tạo,
  // nên không có Chrome thứ hai nào bật lên.
  context: async ({ persistentContext }, use) => {
    await use(persistentContext);
  },

  // Scope = test: mỗi test một tab mới, bắt đầu từ `about:blank` sạch.
  // Đổi lại, mỗi test phải tự `goto*` tới trang nó cần — không ăn ké trang test trước để lại.
  page: async ({ context }, use) => {
    const page = await context.newPage();
    await use(page);
    await page.close();
  },

  // ------------------------------------------------------------------------------------
  // Đăng nhập
  // ------------------------------------------------------------------------------------

  loginPage: async ({ page, appBaseUrl }, use) => {
    await use(new LoginPage(page, appBaseUrl));
  },

  /** Đảm bảo đã đăng nhập app fotowa trước khi truy cập các trang khác. */
  loggedIn: async ({ loginPage, workerCredentials }, use) => {
    await signIn(loginPage, workerCredentials);
    await use();
  },

  /**
   * Đảm bảo CHƯA đăng nhập — dành cho test form login.
   *
   * Profile giữ luôn cookie nên lần chạy sau sẽ vào thẳng trạng thái đã đăng nhập và test không
   * thấy form. Chỉ xoá cookie session của app; cookie SSO (`AWSELBAuthSessionCookie-*`) phải giữ
   * nguyên, xoá là kẹt lại ở Google.
   */
  loggedOut: async ({ context }, use) => {
    await context.clearCookies({ name: APP_SESSION_COOKIE });
    await use();
  },

  // ------------------------------------------------------------------------------------
  // Page object
  // ------------------------------------------------------------------------------------

  // Phụ thuộc `loggedIn` state: page object chỉ được tạo sau khi đăng nhập xong.
  photographerProfilePage: async ({ page, appBaseUrl, appPhotographerPath, loggedIn }, use) => {
    void loggedIn;
    await use(new PhotographerProfilePage(page, appBaseUrl, appPhotographerPath));
  },

  // Không cần `loggedIn`: ta tới trang này bằng click từ calendar, luôn chạy sau khi đã đăng nhập.
  bookingRequestPage: async ({ page, appBaseUrl, appPhotographerPath }, use) => {
    await use(new BookingRequestPage(page, appBaseUrl, appPhotographerPath));
  },

  // ------------------------------------------------------------------------------------
  // Slot còn trống trên calendar
  // ------------------------------------------------------------------------------------

  /**
   * Ngày/giờ của một slot còn trống — **chỉ là dữ liệu**, không để lại state trên tab nào.
   *
   * Tự mở một tab riêng, tìm xong thì đóng lại, nên không test nào ăn ké được vị trí browser.
   * Test cần trang private offer thì tự gọi `gotoBookingRequest(availableSlot)`.
   */
  availableSlot: [
    async ({ persistentContext, appBaseUrl, appPhotographerPath, workerCredentials }, use) => {
      const scratch = await persistentContext.newPage();
      let slot: BookingSlot;
      try {
        await signIn(new LoginPage(scratch, appBaseUrl), workerCredentials);
        slot = await findFirstAvailableSlot(
          new PhotographerProfilePage(scratch, appBaseUrl, appPhotographerPath),
        );
      } finally {
        await scratch.close();
      }
      await use(slot);
    },
    { scope: 'worker' },
  ],

  // Khác `availableSlot` ở chỗ: fixture này đi **đường click thật** và để browser đứng lại ở trang
  // đích. Chỉ dành cho test kiểm tra chính hành vi click (bấm ô → sang đúng URL).
  selectedSlot: async ({ photographerProfilePage }, use) => {
    await use(await findFirstAvailableSlot(photographerProfilePage));
  },
});

/**
 * Thay cho `pytest.skip()` trong fixture `credentials`: pytest cho skip lan truyền xuống mọi test
 * phụ thuộc, Playwright thì không.
 *
 * Dùng trực tiếp khi test cần chính cặp email/password; gọi qua `skipWithoutCredentials()` trong
 * `test.beforeEach` khi test chỉ cần trạng thái đã đăng nhập.
 */
export function requireCredentials(): Credentials {
  const credentials = env.credentials();
  test.skip(credentials === null, 'Must set TEST_EMAIL and TEST_PASSWORD in `.env`');
  if (credentials === null) {
    // Không tới được: `test.skip(true, ...)` đã ném lỗi để dừng test ở dòng trên.
    throw new Error('unreachable');
  }
  return credentials;
}

/** Gọi trong `test.beforeEach` của các file cần đăng nhập — chặn trước khi `workerCredentials` ném. */
export function skipWithoutCredentials(): void {
  requireCredentials();
}

export { expect };
