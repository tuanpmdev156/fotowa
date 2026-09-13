/**
 * Đăng nhập tay một lần qua cổng SSO của staging (AWS Cognito → Google), chạy bằng:
 *     npm run auth
 *
 * Cookie SSO nằm sẵn trong profile Chrome dùng chung (`.auth/chrome-profile`) nên bộ test dùng lại
 * được ngay. File `.auth/storage_state.json` ghi thêm ở cuối **không có code nào đọc** — giữ lại
 * chỉ như một lối thoát thủ công (soi cookie, hoặc tạo context mới khi cần).
 */

// `dotenv/config` PHẢI là import đầu tiên — xem chú thích trong `src/config/env.ts`.
import 'dotenv/config';

import * as fs from 'node:fs';
import * as path from 'node:path';

import { chromium } from '@playwright/test';

import { authStateFile, baseUrl, profileDir, ssoLoginTimeoutMs } from '../src/config/env';

const BASE_URL = baseUrl();
const AUTH_STATE = authStateFile();
const PROFILE_DIR = profileDir();
const LOGIN_TIMEOUT_MS = ssoLoginTimeoutMs();
const APP_HOST = new URL(BASE_URL).host;

/**
 * Trả về true khi đã quay lại đúng host của app.
 *
 * Khi chưa đăng nhập, BASE_URL trả 302 sang Cognito rồi sang Google, nên host lúc đó không phải
 * APP_HOST. `/oauth2/...` bị loại trừ vì đó là bước trung gian của luồng SSO, cookie session chưa
 * chắc đã được set xong.
 */
function isLoggedIn(url: string): boolean {
  const parts = new URL(url);
  return parts.host === APP_HOST && !parts.pathname.startsWith('/oauth2/');
}

async function main(): Promise<number> {
  fs.mkdirSync(PROFILE_DIR, { recursive: true });

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    channel: 'chrome',
    headless: false,
  });
  const page = context.pages()[0] ?? (await context.newPage());
  await page.goto(BASE_URL);

  if (!isLoggedIn(page.url())) {
    console.log(
      `Sign in with Google account in the Chrome window.\n` +
        `Waiting up to ${Math.floor(LOGIN_TIMEOUT_MS / 1000)}s for a redirect back to ${APP_HOST}...`,
    );
    try {
      await page.waitForURL((url) => isLoggedIn(url.toString()), { timeout: LOGIN_TIMEOUT_MS });
    } catch {
      console.error(`\nNever reached a logged-in URL. Still at:\n  ${page.url()}`);
      console.error('Nothing saved - re-run and finish the login.');
      await context.close();
      return 1;
    }
  }

  await page.goto(BASE_URL);
  if (!isLoggedIn(page.url())) {
    console.error(`\nSSO gate is not fully open - redirected back to:\n  ${page.url()}`);
    console.error('Nothing saved - re-run and finish the login.');
    await context.close();
    return 1;
  }

  const finalUrl = page.url();
  fs.mkdirSync(path.dirname(AUTH_STATE), { recursive: true });
  await context.storageState({ path: AUTH_STATE });
  await context.close();

  console.log(`\nLogged in at ${finalUrl}`);
  console.log(`Session saved -> ${AUTH_STATE}`);
  console.log('Tests now reuse it automatically; Chrome can stay open.');
  return 0;
}

main().then(
  (code) => {
    process.exit(code);
  },
  (error: unknown) => {
    console.error(error);
    process.exit(1);
  },
);
