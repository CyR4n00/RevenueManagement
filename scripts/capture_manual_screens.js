const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const output = path.resolve(__dirname, '..', 'docs', 'manual-assets', 'client-guide');
fs.mkdirSync(output, { recursive: true });

function isoDate(date) {
  return date.toISOString().slice(0, 10);
}

function addDays(date, days) {
  const next = new Date(date);
  next.setUTCDate(next.getUTCDate() + days);
  return next;
}

const start = new Date('2026-08-29T00:00:00Z');
const competitors = [
  { id: 'comp-1', name: '山水旅館', url: 'https://www.jalan.net/yad315667/plan/' },
  { id: 'comp-2', name: '源泉湯宿 大成館', url: 'https://www.jalan.net/yad339712/plan/' },
  { id: 'comp-3', name: '後楽園ホテル', url: 'https://travel.rakuten.co.jp/HOTEL/12345/12345.html' },
];

const market = [];
const recommendations = [];
for (let day = 0; day < 90; day += 1) {
  const date = isoDate(addDays(start, day));
  const weekend = addDays(start, day).getUTCDay() === 0 || addDays(start, day).getUTCDay() === 6;
  const prices = [16800 + (day % 5) * 700, 18400 + (day % 4) * 600, 15200 + (day % 6) * 500];
  competitors.forEach((competitor, index) => {
    const soldOut = (day + index * 4) % 19 === 8;
    const limited = !soldOut && (day + index) % 8 === 3;
    market.push({
      date,
      competitor_id: competitor.id,
      competitor_name: competitor.name,
      price_today: soldOut ? 0 : prices[index] + (weekend ? 2400 : 0),
      difference: soldOut ? 0 : [1200, -800, 500][index],
      comparison_available: true,
      comparison_days: 1,
      was_fully_booked: false,
      is_fully_booked: soldOut,
      availability_status: soldOut ? 'sold_out' : limited ? 'limited' : 'available',
      remaining_rooms: limited ? 2 : null,
      availability_source: limited ? 'explicit_count' : 'inferred',
      source: 'apify',
    });
  });
  const average = Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) + (weekend ? 2400 : 0);
  const rank = average >= 20000 ? 'B' : average >= 16000 ? 'C' : 'D';
  recommendations.push({
    date,
    suggested_price: rank === 'B' ? 22000 : rank === 'C' ? 17000 : 12000,
    suggested_rank: rank,
    reasoning: `空室のある比較対象3施設の平均最安値は¥${average.toLocaleString()}です。登録された販売価格表の中から、最も近いランク${rank}を参考表示しています。`,
  });
}

const responses = {
  '/market_data': market,
  '/market_data/cached': market,
  '/alerts': [
    { id: 1, date: isoDate(start), message: '山水旅館が前回より1,200円値上げしました。', type: 'increase' },
    { id: 2, date: isoDate(addDays(start, 8)), message: '後楽園ホテルが部屋なしになりました。', type: 'sold_out' },
  ],
  '/recommendations': recommendations,
  '/competitors': competitors,
  '/billing/status': { configured: true, subscription_status: 'active', plan: 'standard', max_horizon_days: 180, max_competitors: 3 },
  '/facility': {
    min_price: 9000,
    max_price: 30000,
    rate_ranks: [
      { label: 'A', price_jpy: 30000, sort_order: 0 },
      { label: 'B', price_jpy: 22000, sort_order: 1 },
      { label: 'C', price_jpy: 17000, sort_order: 2 },
      { label: 'D', price_jpy: 12000, sort_order: 3 },
    ],
  },
  '/integrations/status': {
    environment: 'production', apify_configured: true, email_delivery_configured: false,
    stripe_configured: true, simulation_enabled: false,
    ota_sources: [
      { key: 'jalan', name: 'じゃらんnet', status: 'approved', actor_configured: true },
      { key: 'rakuten', name: '楽天トラベル', status: 'approved', actor_configured: true },
    ],
  },
  '/notification-settings': { email: 'owner@example.jp', enabled: true, delivery_configured: false },
};

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  });
  const loginPage = await browser.newPage({ viewport: { width: 1200, height: 820 }, deviceScaleFactor: 1 });
  await loginPage.goto('http://localhost:3101/', { waitUntil: 'networkidle' });
  await loginPage.getByRole('heading', { name: 'レベナビ' }).waitFor({ timeout: 15000 });
  await loginPage.screenshot({ path: path.join(output, 'login.png'), fullPage: false });
  await loginPage.close();

  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  await page.route('http://localhost:8000/**', async route => {
    const url = new URL(route.request().url());
    const body = responses[url.pathname] ?? {};
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
  await page.goto('http://localhost:3100/#overview', { waitUntil: 'networkidle' });
  await page.getByText('実データ 90日').waitFor({ timeout: 15000 });
  await page.screenshot({ path: path.join(output, 'dashboard-overview.png'), fullPage: false });

  const targets = [
    ['proposal', 'dashboard-proposal.png'],
    ['tower', 'dashboard-comparison.png'],
    ['calendar', 'dashboard-calendar.png'],
  ];
  for (const [id, filename] of targets) {
    const locator = page.locator(`#${id}`);
    await locator.scrollIntoViewIfNeeded();
    if (id === 'calendar') {
      const details = locator.locator('details').first();
      if (!(await details.evaluate(element => element.open))) {
        await details.locator(':scope > summary').click();
      }
    }
    await page.waitForTimeout(250);
    await locator.screenshot({ path: path.join(output, filename) });
  }

  await page.getByRole('button', { name: '設定' }).click();
  await page.getByRole('heading', { name: '施設設定' }).waitFor();
  await page.locator('[role="dialog"]').screenshot({ path: path.join(output, 'settings.png') });
  await page.getByText('比較する宿', { exact: true }).scrollIntoViewIfNeeded();
  await page.locator('[role="dialog"]').screenshot({ path: path.join(output, 'settings-competitors.png') });

  await browser.close();
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
