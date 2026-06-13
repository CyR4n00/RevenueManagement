import { test, expect } from '@playwright/test';

test('Revenue Control App - Verification', async ({ page }) => {
  await page.goto('http://localhost:3000');

  // Wait for the app to load
  await page.waitForSelector('text=レベニューコントロール');

  // Take a screenshot of the main dashboard
  await page.screenshot({ path: 'screenshots/dashboard.png', fullPage: true });

  // Open settings panel
  await page.click('button:has-text("⚙️ 施設・連携設定")');
  await page.waitForSelector('text=連携システム設定 (OTA / サイトコントローラー)');
  await page.screenshot({ path: 'screenshots/settings_panel.png', fullPage: true });

  // Close settings panel to return to dashboard
  await page.click('button:has-text("閉じる")');

  // Open the calendar modal
  await page.click('button:has-text("📅 カレンダーで過去の費用詳細を確認する")');
  await page.waitForSelector('text=過去の費用（販売価格）カレンダー表示');
  await page.screenshot({ path: 'screenshots/calendar_modal.png', fullPage: true });
});
