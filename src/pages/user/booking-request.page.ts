import { errors, expect, type Locator, type Page } from '@playwright/test';

import { escapeRegExp, pad2, plusOneHour, yen } from '../../utils/format';
import type { BookingSlot } from './photographer-profile.page';

/** Thời gian chờ cảnh báo phí đi xa. Địa điểm không mất phí là dữ liệu hợp lệ, không nên đốt 30s. */
const LONG_DISTANCE_FEE_WARNING_TIMEOUT_MS = 5_000;

/**
 * Đổi text tiền thành số. Ví dụ:
 * - `1,980円` (hậu tố)
 * - `¥1,980` (tiền tố)
 */
function parseYen(text: string): number {
  const digits = text.replace(/\D/g, '');
  if (digits === '') {
    throw new Error(`Couldn't read price from ${JSON.stringify(text)}`);
  }
  return Number.parseInt(digits, 10);
}

export interface ShootingOption {
  readonly label: string;
  readonly price: number;
  readonly selected: boolean;
}

/** Trang đích sau khi chọn một slot trống trên booking calendar. */
export class BookingRequestPage {
  readonly page: Page;
  readonly baseUrl: string;
  readonly photographerPath: string;
  readonly pathPattern: string;

  readonly selectedDatetime: Locator;
  readonly genreSelectionButton: Locator;
  readonly genreOptions: Locator;
  readonly filmingLocation: Locator;
  readonly filmingLocationSuggestionButton: Locator;
  readonly filmingLocationSuggestionList: Locator;
  readonly longDistanceFeeWarning: Locator;
  readonly optionCards: Locator;
  readonly paymentTable: Locator;
  readonly subtotalPrices: Locator;
  readonly optionRows: Locator;
  readonly totalPrice: Locator;
  readonly confirmBookingButton: Locator;

  constructor(page: Page, baseUrl: string, photographerPath: string) {
    this.page = page;
    this.baseUrl = baseUrl;
    this.photographerPath = photographerPath;
    this.pathPattern = `${escapeRegExp(photographerPath)}/private_offers/new`;
    // Selected slot datetime
    this.selectedDatetime = page.locator(
      "//div[@id='app']//div[@class='shootingDateTimeControl__details']",
    );
    // Genre
    this.genreSelectionButton = page.locator("//button[@id='private_offer_creation_form_genre_id']");
    // `:visible` là pseudo-class của CSS, XPath không có — lọc bằng `.filter({ visible: true })`.
    this.genreOptions = page
      .locator("//div[contains(@class,'genreOption')][@data-genre-id][not(@data-genre-id='')]")
      .filter({ visible: true });
    // Filming location
    this.filmingLocation = page.locator("//input[@id='private_offer_creation_form_spot_name']");
    this.filmingLocationSuggestionButton = page.locator("//button[@class='spotControlBtn']");
    this.filmingLocationSuggestionList = page.locator(
      "//div[@class='spotControl__suggest']//div[@class='details']",
    );
    this.longDistanceFeeWarning = page.locator("//div[contains(@class,'longDistanceFee')]");
    // Option cards
    this.optionCards = page.locator("//div[contains(@class,'shootingOptionControl__card')]");
    this.paymentTable = page.locator("//div[@class='payment__table']");
    // Các dòng giá tiền trừ dòng Total(合計).
    this.subtotalPrices = this.paymentTable.locator(
      "//tbody/tr[not(@class='total')]/td[contains(@class,'privateOffers__price')]",
    );
    // Các option đang tick.
    this.optionRows = this.paymentTable.locator("//tbody/tr[@class='option_item']");
    this.totalPrice = this.paymentTable.locator(
      "//tr[@class='total']//td[@class='privateOffers__price']",
    );

    // Submit button
    this.confirmBookingButton = page.locator("//button[@type='submit']");
  }

  // --- Navigation ---

  /**
   * Vào thẳng trang private offer theo slot, không đi vòng qua calendar.
   *
   * Shape URL lấy từ chính `expectSelectedSlotInUrl`.
   */
  async gotoBookingRequest(slot: BookingSlot): Promise<void> {
    await this.page.goto(
      `${this.baseUrl}${this.photographerPath}/private_offers/new` +
        `?shooting_date=${slot.year}-${pad2(slot.month)}-${pad2(slot.day)}` +
        `&shooting_time=${slot.time}`,
    );
  }

  // --- Actions ---

  /** Genre is required field. Chọn genre đầu tiên trong danh sách. */
  async selectFirstGenre(): Promise<void> {
    await this.genreSelectionButton.click();
    await this.genreOptions.first().click();
    await expect(this.optionCards.first()).toBeVisible();
  }

  /** Chọn địa điểm quay phim. */
  async selectFilmingLocation(): Promise<void> {
    await this.filmingLocation.fill('Tokyo Tower');
    await this.filmingLocationSuggestionButton.click();
    await expect(this.filmingLocationSuggestionList.first()).toBeVisible({ timeout: 15_000 });
    await this.filmingLocationSuggestionList.first().click();
  }

  /** Đưa option về trạng thái `selected`. Nếu đã đúng trạng thái thì không bấm nữa. */
  async setOption(label: string, selected = true): Promise<void> {
    const card = this.optionCard(label);
    if (((await card.getAttribute('aria-pressed')) === 'true') === selected) {
      return;
    }
    await card.locator("//label[contains(@class,'shootingOptionControl__mainRow')]").click();
    await expect(card).toHaveAttribute('aria-pressed', selected ? 'true' : 'false');
  }

  // --- Readers ---

  /** Đọc tên/giá/trạng thái của từng option card. */
  async readOptionCards(): Promise<ShootingOption[]> {
    await expect(this.optionCards.first()).toBeVisible({ timeout: 15_000 });
    const cards = await this.optionCards.all();
    if (cards.length === 0) {
      throw new Error('No shooting option cards found on the page.');
    }
    const options: ShootingOption[] = [];
    for (const card of cards) {
      options.push({
        label: await card
          .locator(
            "//p[contains(@class,'shootingOptionControl__title')]" +
              "//span[contains(@class,'typographyBold')]",
          )
          .innerText(),
        price: parseYen(
          await card.locator("//p[contains(@class,'shootingOptionControl__price')]").innerText(),
        ),
        selected: (await card.getAttribute('aria-pressed')) === 'true',
      });
    }
    return options;
  }

  /** Cộng mọi dòng trong bảng giá, trừ dòng Total(合計). Bỏ qua dòng không có giá. */
  async sumSubtotal(): Promise<number> {
    const texts = await this.subtotalPrices.allInnerTexts();
    return texts
      .filter((text) => text.trim() !== '')
      .reduce((total, text) => total + parseYen(text), 0);
  }

  // --- Helper Methods ---

  private optionCard(label: string): Locator {
    return this.optionCards.filter({
      has: this.page.locator("//*[contains(@class,'shootingOptionControl__title')]//span", {
        hasText: label,
      }),
    });
  }

  /** Đọc ô giá theo label, dùng chung cho option và phí di chuyển xa */
  private priceCell(label: string): Locator {
    return this.paymentTable.locator(
      `//tbody/tr[th[normalize-space()='${label}']]/td[contains(@class,'privateOffers__price')]`,
    );
  }

  // --- Assertion ---

  /**
   * Assert đã sang trang tạo private offer, đúng ngày/giờ của ô vừa bấm.
   *
   * URL contains(`?shooting_date=yyyy-MM-dd&shooting_time=HH:MM`)
   */
  async expectSelectedSlotInUrl(slot: BookingSlot): Promise<void> {
    await expect(this.page).toHaveURL(
      new RegExp(
        `^${escapeRegExp(this.baseUrl)}${this.pathPattern}` +
          `\\?shooting_date=${slot.year}-${pad2(slot.month)}-${pad2(slot.day)}` +
          `&shooting_time=${slot.time}`,
      ),
    );
  }

  /** Assert hiển thị đúng ngày/giờ vừa bấm ở calendar. */
  async expectAvailableSlot(slot: BookingSlot): Promise<void> {
    await expect(this.selectedDatetime).toBeVisible({ timeout: 15_000 });
    await expect(this.selectedDatetime).toContainText(
      `${slot.year}/${pad2(slot.month)}/${pad2(slot.day)}`,
    );
    // Assert cả giờ kết thúc: bấm nhầm ô thì không thể pass nhờ ăn may.
    await expect(this.selectedDatetime).toContainText(`${slot.time} - ${plusOneHour(slot.time)}`);
  }

  async expectPaymentTableLoaded(): Promise<void> {
    await expect(this.paymentTable).toBeVisible();
  }

  async expectOptionsLoaded(): Promise<void> {
    await expect(this.optionCards.first()).toBeVisible();
  }

  /** Mặc định trang không tick sẵn option nào. */
  async expectNoOptionSelected(): Promise<void> {
    const selected = (await this.readOptionCards()).filter((o) => o.selected).map((o) => o.label);
    expect(selected).toEqual([]);
    await expect(this.optionRows).toHaveCount(0);
  }

  async expectTotal(expected: number): Promise<void> {
    await expect(this.totalPrice).toHaveText(yen(expected));
  }

  /** Bảng giá khớp đúng những option đang tick: tên, giá và tổng. */
  async expectPaymentTableMatchesSelection(): Promise<void> {
    const selected = (await this.readOptionCards()).filter((option) => option.selected);

    // 1. Bảng có đúng số lượng option đang tick, mỗi dòng đúng cặp tên và giá.
    await expect(this.optionRows).toHaveCount(selected.length);
    for (const option of selected) {
      await expect(this.priceCell(option.label)).toHaveText(yen(option.price));
    }

    // 2. Tổng bằng đúng các dòng đang hiển thị.
    await this.expectTotal(await this.sumSubtotal());
  }

  /** Địa điểm vừa chọn có phát sinh phí đi xa không. */
  async hasLongDistanceFeeWarning(): Promise<boolean> {
    try {
      await this.longDistanceFeeWarning.waitFor({
        state: 'visible',
        timeout: LONG_DISTANCE_FEE_WARNING_TIMEOUT_MS,
      });
    } catch (error) {
      // `catch` trần nuốt mọi lỗi: chỉ timeout mới có nghĩa "không có phí",
      // lỗi khác là bug thật và phải ném tiếp.
      if (error instanceof errors.TimeoutError) {
        return false;
      }
      throw error;
    }
    return true;
  }

  /** Bảng giá có dòng phí di chuyển xa (遠方出張料) với số tiền > 0. */
  async expectLongDistanceFeeCharged(): Promise<void> {
    const cell = this.priceCell('遠方出張料');
    await expect(cell).toBeVisible();
    expect(parseYen(await cell.innerText())).toBeGreaterThan(0);
  }
}
