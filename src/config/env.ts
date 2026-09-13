import * as path from 'node:path';

export interface Credentials {
  readonly email: string;
  readonly password: string;
}

const ROOT = path.resolve(__dirname, '..', '..');

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

/** Tài khoản user fotowa. */
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

/** Chỉ `scripts/save-auth.ts` dùng */
export function authStateFile(): string {
  const configured = read('AUTH_STATE');
  return configured === undefined
    ? path.join(authDir(), 'storage_state.json')
    : path.resolve(ROOT, configured);
}

/** Chỉ `scripts/save-auth.ts` dùng. Mặc định 5 phút để đăng nhập tài khoản Google thủ công. */
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
