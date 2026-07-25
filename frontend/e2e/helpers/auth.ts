import type { Page } from '@playwright/test';

const STORAGE_KEY = 'traffitwin_auth_token';

/**
 * Seeds a valid session JWT before the page loads, via the backend's
 * /auth/dev-login route (disabled in production — see
 * backend/auth/routes.py). Avoids driving the real Google OAuth popup in
 * CI while still exercising the JWT-protected mutating routes end-to-end.
 */
export async function loginAsDevUser(page: Page): Promise<void> {
  const res = await page.request.post('http://localhost:8000/auth/dev-login');
  const { access_token } = await res.json();

  await page.addInitScript(
    ([key, token]) => window.localStorage.setItem(key, token),
    [STORAGE_KEY, access_token]
  );
}
