/**
 * Module DUY NHẤT được phép đọc `process.env`.
 *
 * Bản Python từng dính bẫy thứ tự nạp: `conftest` import `pages.*` trước `load_dotenv()`, nên một
 * `os.getenv` đặt trong thân class âm thầm lấy giá trị mặc định. TypeScript có đúng bẫy đó với
 * `const X = process.env.Y` ở top-level.
 *
 * Cách chặn về mặt cấu trúc: file này export **hàm**, không export hằng. Hàm chỉ chạy khi được gọi,
 * tức là sau khi entry point đã nạp dotenv. Chỉ 2 entry point import `dotenv/config`:
 * `playwright.config.ts` và `scripts/save-auth.ts`.
 */

import * as path from 'node:path';

export interface Credentials {
  readonly email: string;
  readonly password: string;
}

const ROOT = path.resolve(__dirname, '..', '..');

/**
 * Đọc biến môi trường, coi chuỗi rỗng như chưa set.
 *
 * Python `if not (email and password)` bắt cả hai trường hợp; `??` của TS chỉ bắt `undefined`,
 * nên `TEST_EMAIL=` trong `.env` sẽ lọt qua và điền email rỗng vào form login.
 * Không trim: mật khẩu có thể chứa khoảng trắng ở đầu/cuối.
 */
function read(name: string): string | undefined {
  const value = process.env[name];
  return value === undefined || value === '' ? undefined : value;
}

/** URL gốc của môi trường staging. Thiếu là dừng ngay — thay cho `pytest.fail(pytrace=False)`. */
export function baseUrl(): string {
  const url = read('BASE_URL');
  if (url === undefined) {
    throw new Error('BASE_URL is not set. Copy `.env.example` to `.env` and fill in BASE_URL.');
  }
  return url.replace(/\/+$/, '');
}

/** Tài khoản user fotowa. `null` khi thiếu một trong hai — test gọi `skipWithoutCredentials()`. */
export function credentials(): Credentials | null {
  const email = read('TEST_EMAIL');
  const password = read('TEST_PASSWORD');
  if (email === undefined || password === undefined) {
    return null;
  }
  return { email, password };
}

/** Path trang profile của photographer. */
export function photographerPath(): string {
  return `/photographers/${read('PHOTOGRAPHER_NAME') ?? 'bebe'}`;
}

function authDir(): string {
  return path.resolve(ROOT, read('AUTH_DIR') ?? '.auth');
}

/** Profile Chrome dùng chung với `scripts/save-auth.ts`; giữ cookie SSO và disk cache. */
export function profileDir(): string {
  const configured = read('AUTOMATION_PROFILE_DIR');
  return configured === undefined
    ? path.join(authDir(), 'chrome-profile')
    : path.resolve(ROOT, configured);
}

/** Chỉ `scripts/save-auth.ts` dùng. Không có code nào đọc file này — xem chú thích trong script. */
export function authStateFile(): string {
  const configured = read('AUTH_STATE');
  return configured === undefined
    ? path.join(authDir(), 'storage_state.json')
    : path.resolve(ROOT, configured);
}

/** Chỉ `scripts/save-auth.ts` dùng. Mặc định 5 phút để đăng nhập Google bằng tay. */
export function ssoLoginTimeoutMs(): number {
  const raw = read('GOOGLE_SSO_LOGIN_TIMEOUT_MS');
  if (raw === undefined) {
    return 5 * 60 * 1000;
  }
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`GOOGLE_SSO_LOGIN_TIMEOUT_MS is not a positive number: ${raw}`);
  }
  return parsed;
}
