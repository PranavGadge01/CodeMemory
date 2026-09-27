import { test, expect } from '@playwright/test';

const api = 'http://127.0.0.1:8000/api/v1';
test.beforeEach(async ({ request }) => {
  await request.delete(`${api}/leetcode/connect`);
});

test('first launch, public sync, returning launch, submission detail and account switching', async ({ page, request }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(`${page.url()}: ${error.message}`));
  await page.goto('/');
  await page.getByRole('link', { name: 'Get Started' }).click();
  await page.getByLabel('LeetCode username', { exact: true }).fill('alice');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto('/submissions');
  await page.getByRole('link', { name: 'Two Sum', exact: true }).click();
  await expect(page).toHaveURL(/\/submissions\?id=sub-alice$/);
  await expect(page.getByText('alice-private-code', { exact: false })).toBeVisible();
  await expect(page.getByText('bob-private-code', { exact: false })).toHaveCount(0);
  await page.goto('/');
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto('/settings');
  await expect(page.getByText('Connected as @alice.', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Switch account', exact: true }).click();
  await page.getByRole('button', { name: 'Use a different account' }).click();
  await page.getByLabel('LeetCode username', { exact: true }).fill('bob');
  await page.getByRole('button', { name: 'Retry public sync' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await page.goto('/submissions');
  await expect(page.locator('a[href="/submissions?id=sub-alice"]')).toHaveCount(0);
  await page.getByRole('link', { name: 'Two Sum', exact: true }).click();
  await expect(page).toHaveURL(/id=sub-bob$/);
  await expect(page.getByText('bob-private-code', { exact: false })).toBeVisible();
  await page.goto('/revision');
  await expect(page.locator('#revision-topic option')).toHaveText(['All topics', 'Array', 'Hash Table']);
  await page.getByRole('button', { name: 'Mark reviewed', exact: true }).click();
  const detail = await (await request.get(`${api}/problems/two-sum`)).json();
  expect(JSON.stringify(detail)).not.toContain('alice-private-note');
  for (const path of ['/search', '/analytics', '/knowledge', '/problems']) {
    await page.goto(path);
    await expect(page.locator('#cm-main')).toBeVisible();
  }
  await page.goto('/settings');
  await page.getByRole('button', { name: 'Disconnect', exact: true }).click();
  await page.getByRole('button', { name: 'Disconnect', exact: true }).click();
  await expect(page).toHaveURL(/\/connect$/);
  await expect(page.getByLabel('LeetCode username', { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('failed optimistic settings patch preserves the later successful patch and restart', async ({ page, request }) => {
  await request.put(`${api}/settings`, { data: { accentEmphasis: true, compactDensity: false } });
  let writes = 0;
  await page.route('**/api/v1/settings', async (route) => {
    if (route.request().method() !== 'PUT' || ++writes !== 1) return route.continue();
    await new Promise((resolve) => setTimeout(resolve, 400));
    await route.fulfill({ status: 500, json: { error: { code: 'TEST_FAILURE', message: 'Could not save accent preference.' } } });
  });
  await page.goto('/settings');
  const accent = page.getByRole('switch', { name: 'Accent emphasis' });
  const density = page.getByRole('switch', { name: 'Compact density' });
  await expect(accent).toBeEnabled();
  await accent.click();
  await density.click();
  await expect(page.getByRole('alert').filter({ hasText: 'Could not save accent preference.' })).toBeVisible();
  await expect(accent).toHaveAttribute('aria-checked', 'true');
  await expect(density).toHaveAttribute('aria-checked', 'true');
  await expect.poll(async () => (await (await request.get(`${api}/settings`)).json()).compactDensity).toBe(true);
  await page.reload();
  await expect(density).toHaveAttribute('aria-checked', 'true');
});

test('website homepage and download are responsive and independent', async ({ page }) => {
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto('http://127.0.0.1:4173/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Your coding history,remembered.');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `../build/browser/website-${width}.png`, fullPage: true });
    await page.getByRole('link', { name: 'Download for Windows', exact: true }).first().click();
    await expect(page.getByRole('heading', { name: 'CodeMemory for Windows' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `../build/browser/download-${width}.png`, fullPage: true });
  }
});
