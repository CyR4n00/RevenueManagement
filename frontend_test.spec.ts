import { test, expect } from '@playwright/test';

test('Revenue Assistant - Competitor Dashboard Verification', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // Bypass login screen
  await page.click('button:has-text("[開発用] 決済をスキップしてログイン")');

  // Wait for the app to load and Revenue Tower to be visible
  await page.waitForSelector('text=レベニューカレンダー');
  await page.waitForTimeout(1000); // Wait for data to render

  // Take a screenshot of the main dashboard
  await page.screenshot({ path: 'screenshots/dashboard_competitor.png', fullPage: true });

  // Open settings panel
  await page.click('button:has-text("⚙️ ベンチマーク設定")');
  await page.waitForSelector('text=1. ベンチマーク（競合）登録');

  // Verify API Key input is NOT present
  await expect(page.locator('label[for="apify-api-key"]')).toBeHidden();

  await page.screenshot({ path: 'screenshots/settings_competitor.png', fullPage: true });
  await page.click('button:has-text("設定を保存して戻る")');

  // Verify panel closed
  await page.waitForSelector('text=⚙️ ベンチマーク設定', { state: 'visible' });

});
