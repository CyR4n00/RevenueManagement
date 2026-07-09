import { test, expect } from '@playwright/test';

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

  // Verify API Key input is present
  await page.waitForSelector('label[for="apify-api-key"]');
  const input = page.locator('#apify-api-key');
  await expect(input).toBeVisible();

  // Enter API Key and save
  await input.fill('test_api_key_123');
  await page.screenshot({ path: 'screenshots/settings_competitor_with_api_key.png', fullPage: true });
  await page.click('button:has-text("設定を保存して戻る")');

  // Verify panel closed
  await page.waitForSelector('text=⚙️ ベンチマーク設定', { state: 'visible' });

});
