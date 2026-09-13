import { skipWithoutCredentials, test } from '../src/fixtures/test';

test.beforeEach(() => {
  skipWithoutCredentials();
});

// `selectedSlot` đi đường click thật trên calendar — đây là test của chính hành vi click đó,
// nên không dùng `gotoBookingRequest`.
test('TC_01_selected_slot_is_displayed', async ({ bookingRequestPage, selectedSlot }) => {
  // Assert URL trước: sai trang thì fail ngay ở đây thay vì chờ hết timeout của element.
  await bookingRequestPage.expectSelectedSlotInUrl(selectedSlot);
  await bookingRequestPage.expectAvailableSlot(selectedSlot);
});

/** Chưa tick option nào. */
test('TC_02_no_option_in_payment_table', async ({ bookingRequestPage, availableSlot }) => {
  await bookingRequestPage.gotoBookingRequest(availableSlot);
  await bookingRequestPage.expectPaymentTableLoaded();
  await bookingRequestPage.expectOptionsLoaded();
  await bookingRequestPage.expectNoOptionSelected();
  await bookingRequestPage.expectPaymentTableMatchesSelection();
});

/** Từng option: tick thì bảng hiện đúng tên option + giá và cộng vào tổng, bỏ tick thì trừ lại. */
test('TC_03_select_an_option_in_payment_table', async ({ bookingRequestPage, availableSlot }) => {
  await bookingRequestPage.gotoBookingRequest(availableSlot);
  for (const option of await bookingRequestPage.readOptionCards()) {
    await bookingRequestPage.setOption(option.label, true);
    await bookingRequestPage.expectPaymentTableMatchesSelection();

    await bookingRequestPage.setOption(option.label, false);
    await bookingRequestPage.expectPaymentTableMatchesSelection();
  }
});

/** Tick cả hai option: đủ hai dòng và tổng cộng đủ cả hai. */
test('TC_04_select_multiple_options_in_payment_table', async ({
  bookingRequestPage,
  availableSlot,
}) => {
  await bookingRequestPage.gotoBookingRequest(availableSlot);
  const options = await bookingRequestPage.readOptionCards();
  // Tick các option
  for (const option of options) {
    await bookingRequestPage.setOption(option.label, true);
  }
  await bookingRequestPage.expectPaymentTableMatchesSelection();

  // Bỏ tick các option
  for (const option of await bookingRequestPage.readOptionCards()) {
    await bookingRequestPage.setOption(option.label, false);
  }
  await bookingRequestPage.expectNoOptionSelected();
  await bookingRequestPage.expectPaymentTableMatchesSelection();
});

/** Địa điểm có cảnh báo phí đi xa và tổng tiền có cộng khoản đó. */
test('TC_05_long_distance_fee_in_payment_table', async ({ bookingRequestPage, availableSlot }) => {
  await bookingRequestPage.gotoBookingRequest(availableSlot);
  await bookingRequestPage.selectFirstGenre();
  await bookingRequestPage.selectFilmingLocation();
  test.skip(
    !(await bookingRequestPage.hasLongDistanceFeeWarning()),
    'Địa điểm đã chọn không phát sinh phí đi xa.',
  );
  await bookingRequestPage.expectLongDistanceFeeCharged();
  await bookingRequestPage.expectPaymentTableMatchesSelection();
});
