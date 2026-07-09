import { test, expect } from '@playwright/test';

test('loading state has correct accessible attributes and visual styles', async ({ page }) => {
  // Mock the API requests with a delay to ensure loading state is visible
  await page.route('**/market_data*', async route => {
    // Delay to simulate network latency
    await new Promise(resolve => setTimeout(resolve, 500));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    });
  });

  await page.route('**/alerts*', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    });
  });

  await page.route('**/recommendation*', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        date: "2026-07-20",
        suggested_price: 15000,
        suggested_rank: "A",
        reasoning: "Mock recommendation"
      })
    });
  });

  // Navigate to the app
  await page.goto('http://localhost:3000');

  // Verify the main container gets the loading state
  const mainContainer = page.locator('div[aria-busy]');

  // Wait for the container to become visible and check its state
  await expect(mainContainer).toHaveAttribute('aria-busy', 'true');
  await expect(mainContainer).toHaveClass(/opacity-50/);
  await expect(mainContainer).toHaveClass(/pointer-events-none/);

  // Wait for the loading state to complete
  await expect(mainContainer).toHaveAttribute('aria-busy', 'false');
  await expect(mainContainer).not.toHaveClass(/opacity-50/);
  await expect(mainContainer).not.toHaveClass(/pointer-events-none/);
});

test('Revenue Assistant - Competitor Dashboard Verification', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // Wait for the app to load and Revenue Tower to be visible
  await page.waitForSelector('text=レベニューカレンダー');
  await page.waitForTimeout(1000); // Wait for data to render

  // Take a screenshot of the main dashboard
  await page.screenshot({ path: 'screenshots/dashboard_competitor.png', fullPage: true });

  // Open settings panel
  await page.click('button:has-text("⚙️ ベンチマーク設定")');
  await page.waitForSelector('text=OTAのURL');
  await page.screenshot({ path: 'screenshots/settings_competitor.png', fullPage: true });

});
