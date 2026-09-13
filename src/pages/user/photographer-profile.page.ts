import { expect, type Locator, type Page } from '@playwright/test';

/** Ngày/giờ của ô calendar vừa được chọn. */
export interface BookingSlot {
  readonly year: number;
  readonly month: number;
  readonly day: number;
  /** "HH:MM" */
  readonly time: string;
}

// Javascript function kiểm tra ngày đầu tiên trong tuần đã thay đổi hay chưa, so với giá trị cũ.
function firstDayChanged(old: string): boolean {
  const cell = document.querySelector<HTMLElement>('table.calendar__header tr.dayname td');
  return (cell?.innerText.trim() ?? old) !== old;
}

/** Trang chi tiết photographer */
export class PhotographerProfilePage {
  // Calendar chỉ hiện 7 ngày.
  // Khi kín lịch bấm 次週 để tìm lịch trống, tối đa MAX_WEEKS lần, nếu vẫn kín lịch sau đó thì fail.
  static readonly MAX_WEEKS = 10;

  readonly page: Page;
  readonly baseUrl: string;
  readonly photographerPath: string;

  readonly calendar: Locator;
  readonly nextWeekLink: Locator;
  readonly bookingTableHeader: Locator;
  readonly bookingTable: Locator;
  readonly currentYearMonth: Locator;
  readonly dayHeaders: Locator;
  readonly timeSlots: Locator;
  readonly availableDates: Locator;

  constructor(page: Page, baseUrl: string, photographerPath: string) {
    this.page = page;
    this.baseUrl = baseUrl;
    this.photographerPath = photographerPath;

    this.calendar = page.locator("//div[@class='calendar']//table[@class='calendar__timeContainer']");
    this.nextWeekLink = page.locator("//li[@class='next']/a[text()='次週']");

    this.bookingTableHeader = page.locator("//table[@class='calendar__header']");
    // Table cho mỗi tuần (7 cột, 24 hàng).
    this.bookingTable = this.calendar.locator("//table[@class='events']");
    this.currentYearMonth = this.bookingTableHeader.locator("//tr[@class='month']/th[@colspan]");
    // Cột ngày
    this.dayHeaders = this.bookingTableHeader.locator("//tr[@class='dayname']/td");
    // Cột giờ
    this.timeSlots = this.calendar.locator("//table[@class='time']//td");
    this.availableDates = this.calendar.locator("//td[@class='available']");
  }

  // --- Navigation ---

  async gotoProfilePage(): Promise<void> {
    await this.page.goto(`${this.baseUrl}${this.photographerPath}`);
  }

  /** Bấm next và chờ calendar render xong tuần mới. */
  async gotoNextWeek(): Promise<void> {
    const firstDayInWeek = (await this.dayHeaders.first().innerText()).trim();
    await this.nextWeekLink.click();
    // Cổng chờ phải là `waitForFunction` (ô tồn tại VÀ đã khác giá trị cũ):
    // `not.toHaveText` pass ngay khoảnh khắc Vue gỡ `td` ra giữa lúc re-render.
    await this.page.waitForFunction(firstDayChanged, firstDayInWeek);
  }

  /**
   * Bấm sang tuần kế tiếp cho tới khi calendar có ít nhất một slot trống.
   * Nếu sau MAX_WEEKS lần bấm vẫn không có slot trống thì fail.
   */
  async gotoWeekWithAvailableDate(): Promise<void> {
    for (let clicked = 0; clicked <= PhotographerProfilePage.MAX_WEEKS; clicked += 1) {
      // `count()` chứ không phải `expect`: tuần kín lịch là dữ liệu bình thường,
      // chờ hết 30s timeout cho mỗi tuần là quá đắt.
      if ((await this.availableDates.count()) > 0) {
        return;
      }
      if (clicked < PhotographerProfilePage.MAX_WEEKS) {
        await this.gotoNextWeek();
      }
    }

    throw new Error(`No available slot after clicking ${PhotographerProfilePage.MAX_WEEKS} week times`);
  }

  // --- Actions ---

  /** Click slot trống đầu tiên, trả về ngày/giờ của chính ô đó. */
  async selectFirstAvailableSlot(): Promise<BookingSlot> {
    const columns = await this.bookingTable.count();
    for (let column = 0; column < columns; column += 1) {
      const cells = this.bookingTable.nth(column).locator('//tr/td');
      // Lấy class của cả cột trong một lần gọi thay vì hỏi từng ô.
      const classes = await cells.evaluateAll<string[], void, HTMLElement>((els) =>
        els.map((el) => el.className),
      );
      for (const [row, css] of classes.entries()) {
        // Tách theo khoảng trắng, KHÔNG dùng `css.includes('available')` —
        // chuỗi đó khớp cả `unavailable`.
        const names = css.split(/\s+/);
        if (names.includes('available') && !names.includes('outdated')) {
          const slot = await this.readSlot(column, row);
          await cells.nth(row).click();
          return slot;
        }
      }
    }

    throw new Error('No available slot in the calendar');
  }

  // --- Private Methods ---

  private async readSlot(column: number, row: number): Promise<BookingSlot> {
    const [year, month] = await this.readYearMonth(column);
    const day = await this.dayHeaders.nth(column).locator('//span').innerText();
    return {
      year,
      month,
      day: Number.parseInt(day.trim(), 10),
      time: (await this.timeSlots.nth(row).innerText()).trim(),
    };
  }

  /** Năm/tháng của tuần đang hiển thị. */
  private async readYearMonth(column: number): Promise<[number, number]> {
    // Một tuần vắt qua 2 tháng sẽ render 2 `th[@colspan]`, nên phải cộng dồn colspan
    // để biết cột này rơi vào tháng nào.
    const cells = await this.currentYearMonth.evaluateAll<Array<[number, string]>, void, HTMLTableCellElement>(
      (els) => els.map((el) => [el.colSpan, el.innerText.trim()]),
    );
    let cursor = 0;
    for (const [span, text] of cells) {
      cursor += span;
      if (column < cursor) {
        const [year, month] = text.split('/');
        if (year === undefined || month === undefined) {
          throw new Error(`Couldn't read year/month from ${JSON.stringify(text)}`);
        }
        return [Number.parseInt(year, 10), Number.parseInt(month, 10)];
      }
    }

    throw new Error(`Column ${column} is outside the booking calendar`);
  }

  // --- Assertion ---

  async expectCalendarLoaded(): Promise<void> {
    await expect(this.calendar).toBeVisible();
  }

  async expectHasAvailableDate(): Promise<void> {
    // Tìm tuần có slot trống trước, rồi mới assert
    await this.gotoWeekWithAvailableDate();
    await expect(this.availableDates).not.toHaveCount(0);
  }
}
