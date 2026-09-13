import { skipWithoutCredentials, test } from '../src/fixtures/test';

test.beforeEach(() => {
  skipWithoutCredentials();
});

test('TC_01_booking_calendar_is_displayed', async ({ photographerProfilePage }) => {
  await photographerProfilePage.gotoProfilePage();
  await photographerProfilePage.expectCalendarLoaded();
});

test('TC_02_booking_calendar_has_available_date', async ({ photographerProfilePage }) => {
  await photographerProfilePage.gotoProfilePage();
  await photographerProfilePage.expectHasAvailableDate();
});
