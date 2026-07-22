import { test, expect } from '@playwright/test';

test('injecting a sensor failure surfaces it in the event log', async ({ page }) => {
  await page.goto('/');

  // Dismiss the startup briefing modal so it doesn't intercept clicks.
  await page.getByRole('button', { name: 'Dismiss briefing' }).click();

  await page.getByRole('button', { name: 'Inject sensor failure' }).click();

  const dialog = page.getByRole('dialog', { name: 'INJECT SENSOR FAILURE' });
  // The sensor ID and duration inputs aren't associated with their <label>s
  // via htmlFor/id, so target them positionally instead of by accessible name.
  await dialog.locator('input').nth(0).fill('42');
  await dialog.locator('input').nth(1).fill('5');
  await dialog.getByRole('button', { name: 'INJECT', exact: true }).click();

  await expect(dialog).not.toBeVisible();

  // Open the event log drawer and confirm the fault was recorded.
  await page.getByRole('button', { name: 'Event Log' }).click();
  await expect(page.getByText('Manual failure injected on Sensor 42')).toBeVisible();
});
