import { test, expect } from '@playwright/test';

test('auto play advances the simulation and disables manual stepping until paused', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Dismiss briefing' }).click();

  const stepButton = page.getByRole('button', { name: 'Step simulation by one time step' });
  const autoplayButton = page.getByRole('button', { name: 'Start auto play' });

  await expect(stepButton).toBeEnabled();

  await autoplayButton.click();

  // While autoplay is running, manual stepping is disabled and the button
  // relabels to let the user pause it.
  await expect(stepButton).toBeDisabled();
  const pauseButton = page.getByRole('button', { name: 'Stop auto play' });
  await expect(pauseButton).toBeVisible();
  await expect(pauseButton).toHaveAttribute('aria-pressed', 'true');

  // Let it run for a couple of ticks so the simulation actually advances.
  await page.waitForTimeout(3000);

  await pauseButton.click();

  await expect(stepButton).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Start auto play' })).toBeVisible();
});
