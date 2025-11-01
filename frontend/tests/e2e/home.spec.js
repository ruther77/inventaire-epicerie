import { test, expect } from '@playwright/test';

test.describe('Home navigation', () => {
  test('renders the landing hero and saved views', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /Que souhaitez-vous faire/ })).toBeVisible();
    await expect(page.getByText('Stock faible')).toBeVisible();
  });
});
