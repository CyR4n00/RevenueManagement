import { test, expect } from '@playwright/test';

test('Revenue Assistant - Decision Support Dashboard Verification', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // Wait for the app to load and Revenue Tower to be visible
  await page.waitForSelector('text=レベニューカレンダー');
  await page.waitForTimeout(1000); // Wait for data to render

  // Take a screenshot of the main dashboard
  await page.screenshot({ path: 'screenshots/dashboard_decision_support.png', fullPage: true });

  // Open settings panel
  await page.click('button:has-text("⚙️ 管理者設定")');
  await page.waitForSelector('text=⚙️ 管理者専用セットアップ');
  await page.screenshot({ path: 'screenshots/settings_admin.png', fullPage: true });

});
