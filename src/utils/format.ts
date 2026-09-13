/** Vài tiện ích Python lấy sẵn từ stdlib, TS phải tự viết. */

/** `8` → `"08"` (thay cho `f"{n:02d}"`). */
export function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

/**
 * `1980` → `"¥1,980"` (thay cho `f"¥{n:,}"`).
 *
 * Locale bị pin cứng `en-US`: để `toLocaleString()` tự chọn thì máy chạy locale `de-DE` sẽ render
 * `¥24.200` và mọi assert về tiền sẽ sai.
 */
export function yen(amount: number): string {
  return `¥${amount.toLocaleString('en-US')}`;
}

/** `"08:00"` → `"09:00"`. Một buổi chụp mặc định dài 1 tiếng; 23:00 quay vòng về 00:00. */
export function plusOneHour(hhmm: string): string {
  const [rawHour, rawMinute] = hhmm.split(':');
  if (rawHour === undefined || rawMinute === undefined) {
    throw new Error(`Couldn't read time from ${JSON.stringify(hhmm)}`);
  }
  const hour = Number(rawHour);
  const minute = Number(rawMinute);
  if (!Number.isInteger(hour) || !Number.isInteger(minute)) {
    throw new Error(`Couldn't read time from ${JSON.stringify(hhmm)}`);
  }
  return `${pad2((hour + 1) % 24)}:${pad2(minute)}`;
}

/** Thay cho `re.escape` — Node chưa có `RegExp.escape`. */
export function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
