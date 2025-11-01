import { test, expect } from '@playwright/test';

test.describe('Home navigation', () => {
  test('renders the landing hero and saved views', async ({ page }) => {
    // Ensure the page is fully loaded before checking for elements
    await page.goto('/app/', { waitUntil: 'networkidle' });

    const heading = page.getByRole('heading', { name: /Que souhaitez-vous faire|What would you like to do/i });
    try {
      await expect(heading).toBeVisible({ timeout: 10000 });
    } catch (e) {
      console.error('Heading not found. Page HTML below:\n', await page.content());
      throw e;
    }

    try {
      await expect(page.getByText(/Stock faible|Low stock/i)).toBeVisible({ timeout: 10000 });
    } catch (e) {
      console.error('Saved view text not found. Page HTML below:\n', await page.content());
      throw e;
    }
  });
});
