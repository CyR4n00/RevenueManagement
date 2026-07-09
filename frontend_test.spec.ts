import { test, expect } from '@playwright/test';

test('Revenue Assistant - Competitor Dashboard Verification', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // Wait for the app to load and Revenue Tower to be visible
  await page.waitForSelector('text=マーケットトレンドダッシュボード');
  await page.waitForTimeout(1000); // Wait for data to render

  // Take a screenshot of the main dashboard
  await page.screenshot({ path: 'screenshots/dashboard_competitor.png', fullPage: true });

  // Open settings panel
  await page.click('button:has-text("⚙️ ベンチマーク設定")');
  await page.waitForSelector('text=OTAのURL');
  await page.screenshot({ path: 'screenshots/settings_competitor.png', fullPage: true });

});
