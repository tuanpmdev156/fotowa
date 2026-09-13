# Dự án Automation fotowa

Bộ test UI end-to-end cho dự án fotowa, viết bằng
[Playwright](https://playwright.dev/) + TypeScript theo mô hình POM (Page Object Model).

---

## Cấu hình

| Công cụ | Phiên bản | Ghi chú |
|---|---|---|
| Node.js | 24 LTS | `node -v` phải ra ít nhất `v22`; máy đang dùng `v24.15.0` |
| npm | đi kèm Node | Toàn bộ dependency nằm trong `devDependencies` |
| `@playwright/test` | 1.63.0 | Test runner chính thức của Playwright |
| TypeScript | 7.0.2 | Chỉ dùng để type-check (`tsc --noEmit`), không build ra JS |
| Google Chrome | đã cài sẵn trong máy | Test chạy bằng `channel: 'chrome'`, **không** dùng Chromium đi kèm Playwright |

Cần một tài khoản Google fotowa có quyền truy cập trang staging để làm được bất cứ việc gì sau
trang đăng nhập.

### Biến môi trường

Copy `.env.example` thành `.env` rồi điền giá trị. 
`.env` đã được gitignore — tuyệt đối không commit file này.

Bắt buộc phải điền `BASE_URL`, `TEST_EMAIL`, `TEST_PASSWORD`. 
Các biến còn lại đều có default trong code, đáng chú ý nhất là `PHOTOGRAPHER_NAME` (default = `bebe`)


Biến set sẵn trong shell sẽ thắng `.env`, dùng để ghi đè tạm cho một lần chạy:

```powershell
$env:BASE_URL = "https://moi-truong-khac.fotowa.com"
$env:PHOTOGRAPHER_NAME = "bebe"
```

---

## Cài đặt

Toàn bộ câu lệnh là PowerShell, chạy từ thư mục gốc của dự án.

```powershell
# 1. dependency (KHÔNG chạy `npx playwright install`- dùng Chrome hệ thống)
npm install

# 2. cấu hình
Copy-Item .env.example .env
notepad .env

# 3. đăng nhập SSO tay một lần
npm run auth
```

Bước 3 mở một cửa sổ Chrome với profile automation riêng (`.auth/chrome-profile`). Hoàn tất
đăng nhập Google,sau khi trình duyệt quay về trang chủ của Fotowa là xong. 
Các test case sẽ dùng lại **đúng profile đó**

---

## Chạy test

```powershell
# kiểm tra tĩnh: tsc --noEmit + liệt kê test, vài giây, không mở browser
npm run check

# tất cả test case
npm test

# một test case cụ thể (khớp theo tên, là regex)
npx playwright test -g "TC_01_login_form_is_displayed"

# một file
npx playwright test e2e/user-01-login.spec.ts

# chạy chậm lại để quan sát
npx playwright test --debug

# ghi trace rồi mở xem
npx playwright test --trace on
npx playwright show-trace test-results\<thu-muc-test>\trace.zip

# mở HTML report của lần chạy gần nhất
npm run report
```

Ảnh chụp màn hình nằm trong `test-results/<ten-test>/`: `test-failed-*.png` khi fail và
`test-finished-*.png` khi pass. 

Mỗi lần chụp ra **2 file** vì
`launchPersistentContext` tự mở sẵn một tab trắng và Playwright chụp mọi tab đang mở — file thứ hai
mới là tab của test.

Muốn đổi chế độ screenshot thì sửa
`playwright.config.ts`:

```ts
screenshot: { mode: 'only-on-failure', fullPage: true }   // mặc định
screenshot: { mode: 'on', fullPage: true }                // chụp cả test pass
screenshot: 'off'                                         // không chụp
```

---

## Cấu trúc thư mục

```
fotowa-automation-project/
├── e2e/                      # 9 test case (*.spec.ts), mỗi file một nhóm chức năng
├── src/
│   ├── config/               # env.ts — nơi duy nhất đọc biến môi trường
│   ├── fixtures/             # test.ts — toàn bộ fixture + signIn()
│   ├── pages/                # Page Object (*.page.ts), chia theo role rồi tới trang
│   └── utils/                # format.ts — pad2 / yen / plusOneHour / escapeRegExp
├── scripts/                  # save-auth.ts — đăng nhập Google SSO tay (`npm run auth`)
├── dom-snapshots/            # DOM đã lưu để viết XPath offline (số liệu đã cũ)
├── planS/                    # Ghi chép kế hoạch từng mảng việc
├── .auth/                    # (gitignore) chrome-profile giữ cookie SSO + cache
├── test-results/             # (gitignore) screenshot khi test fail
├── playwright-report/        # (gitignore) HTML report
├── playwright.config.ts      # testDir, workers, channel chrome, screenshot...
├── tsconfig.json             # strict, noEmit — chỉ để type-check
├── package.json              # npm scripts: test / check / auth / report
├── .env / .env.example       # `.env` là giá trị thật, đã gitignore
├── CLAUDE.md                 # Context cho Claude Code
├── TODO.md                   # Backlog + "Lưu ý khi viết test"
└── README.md
```


---

## Lưu ý khi viết test

Xem `TODO.md`, mục **Lưu ý khi viết test**.
