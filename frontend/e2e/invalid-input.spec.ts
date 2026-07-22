import { test, expect } from '@playwright/test';

test('rejects an invalid sensor failure injection and keeps the modal open', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Dismiss briefing' }).click();

  await page.getByRole('button', { name: 'Inject sensor failure' }).click();
  const dialog = page.getByRole('dialog', { name: 'INJECT SENSOR FAILURE' });

  // A value like 999 would violate the input's native max=30 constraint and
  // the browser blocks submission before our own validation ever runs, so a
  // blank (non-required) field is used to exercise the app-level check.
  await dialog.locator('input').nth(0).fill('10');
  await dialog.locator('input').nth(1).fill('');
  await dialog.getByRole('button', { name: 'INJECT', exact: true }).click();

  await expect(dialog.getByText('Duration must be 1–30 steps')).toBeVisible();
  await expect(dialog).toBeVisible(); // modal stays open, nothing was submitted

  // Cancelling closes the modal (its backdrop would otherwise intercept
  // clicks on the rest of the page) without side effects.
  await dialog.getByRole('button', { name: 'CANCEL' }).click();
  await expect(dialog).not.toBeVisible();

  // No fault event should have been recorded for this rejected attempt.
  await page.getByRole('button', { name: 'Event Log' }).click();
  await expect(page.getByText('Manual failure injected on Sensor 10')).not.toBeVisible();
});
