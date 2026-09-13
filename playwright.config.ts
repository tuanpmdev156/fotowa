// `dotenv/config` PHẢI là import đầu tiên: nó nạp `.env` trước khi bất kỳ module nào khác
// được đánh giá. Đây là bẫy đã từng dính ở bản Python (conftest import pages.* trước
// load_dotenv, nên os.getenv trong thân class âm thầm lấy giá trị mặc định).
// Chỉ 2 entry point được phép import dotenv: file này và scripts/save-auth.ts.
import 'dotenv/config';

import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',

  // workers: 1 KHÔNG phải tham số tinh chỉnh. launchPersistentContext giữ khoá độc quyền
  // trên thư mục profile (.auth/chrome-profile), nên worker thứ hai không thể mở nổi.
  // Đây cũng là thứ khiến worker-scoped fixture hành xử đúng như session scope của pytest.
  workers: 1,
  fullyParallel: false,

  // Không retry: suite chạy trên staging thật, retry sẽ che giấu test lệ thuộc thứ tự.
  retries: 0,

  reporter: [['list'], ['html', { open: 'never' }]],
  outputDir: './test-results',

  use: {
    channel: 'chrome', // Google Chrome đã cài sẵn, không dùng bundled chromium
    headless: false,
    // `fullPage: true` để giữ đúng hành vi bản Python (`page.screenshot(full_page=True)`);
    // mặc định của Playwright chỉ chụp phần viewport.
    screenshot: { mode: 'only-on-failure', fullPage: true },

    // Giữ nguyên default của Playwright: 30s cho action/navigation, 5s cho expect.
    actionTimeout: 0,
    navigationTimeout: 0,
  },

  expect: { timeout: 5_000 },
});
