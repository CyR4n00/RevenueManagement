import { Actor } from 'apify';
import { PlaywrightCrawler, log } from 'crawlee';

const OTA = {
    key: 'jalan',
    name: 'Jalan',
    allowedHosts: ['www.jalan.net', 'jalan.net'],
    soldOutPattern: /(満室|空室なし|ご予約いただけません|予約できません|sold\s*out|no\s*availability)/i,
};

const DATE_SELECTORS = {
    checkIn: [
        'input[name*="checkin" i]', 'input[name*="check_in" i]',
        'input[id*="checkin" i]', '[data-testid*="checkin" i] input',
    ],
    checkOut: [
        'input[name*="checkout" i]', 'input[name*="check_out" i]',
        'input[id*="checkout" i]', '[data-testid*="checkout" i] input',
    ],
};
const ADULT_SELECTORS = [
    'select[name*="adult" i]', 'select[id*="adult" i]',
    'input[name*="adult" i]', 'input[id*="adult" i]',
];
const SEARCH_PATTERN = /(検索|空室|プランを探す|宿泊日を変更|search|availability)/i;

function asUrl(value) {
    const url = new URL(value);
    if (url.protocol !== 'https:' || !OTA.allowedHosts.includes(url.hostname.toLowerCase())) {
        throw new Error(`Only approved ${OTA.name} HTTPS property URLs are accepted`);
    }
    return url.toString();
}

function asDate(value, name) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value ?? '') || Number.isNaN(Date.parse(`${value}T00:00:00Z`))) {
        throw new Error(`${name} must be a YYYY-MM-DD date`);
    }
    return value;
}

function asStayDates(values) {
    if (!Array.isArray(values) || values.length < 1 || values.length > 31) {
        throw new Error('stayDates must contain between 1 and 31 dates');
    }
    const dates = [...new Set(values.map((value) => asDate(value, 'stayDates item')))];
    if (dates.length !== values.length) throw new Error('stayDates must not contain duplicates');
    return dates;
}

function nextDate(value) {
    const date = new Date(`${value}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() + 1);
    return date.toISOString().slice(0, 10);
}

function priceCandidates(text) {
    const candidates = [];
    for (const match of text.matchAll(/(?:¥|￥)\s*([\d,]+)/g)) candidates.push(match[1]);
    for (const match of text.matchAll(/([\d,]+)\s*円/g)) candidates.push(match[1]);
    return candidates
        .map((value) => Number.parseInt(value.replaceAll(',', ''), 10))
        .filter((value) => Number.isFinite(value) && value >= 3_000 && value <= 1_000_000);
}

async function fillFirstVisible(page, selectors, value) {
    for (const selector of selectors) {
        const locator = page.locator(selector).first();
        if (await locator.count() && await locator.isVisible().catch(() => false)) {
            if (await locator.getAttribute('readonly') !== null) {
                await page.keyboard.press('Escape').catch(() => undefined);
                await locator.click();
                await page.waitForTimeout(300);
                const calendarDay = page.locator(`[data-time="${Date.parse(`${value}T00:00:00Z`)}"]:not(.not-available)`).first();
                if (!await calendarDay.count() || !await calendarDay.isVisible().catch(() => false)) {
                    log.warning('Requested date is not selectable in the calendar', { selector, value });
                    return false;
                }
                await calendarDay.click();
                return true;
            }
            await locator.fill(value);
            await locator.dispatchEvent('change');
            await locator.dispatchEvent('input');
            return true;
        }
    }
    return false;
}

async function setAdultCount(page, adults) {
    for (const selector of ADULT_SELECTORS) {
        const locator = page.locator(selector).first();
        if (!await locator.count() || !await locator.isVisible().catch(() => false)) continue;
        if (await locator.evaluate((element) => element.tagName === 'SELECT')) {
            await locator.selectOption({ label: String(adults) }).catch(async () => locator.selectOption(String(adults)));
        } else {
            await locator.fill(String(adults));
            await locator.dispatchEvent('change');
        }
        return true;
    }
    return false;
}

async function submitAvailabilitySearch(page) {
    const buttons = page.getByRole('button', { name: SEARCH_PATTERN });
    if (await buttons.count()) {
        await buttons.first().click();
        await page.waitForLoadState('domcontentloaded').catch(() => undefined);
        return true;
    }
    const inputs = page.locator('input[type="submit"], button');
    const count = await inputs.count();
    for (let index = 0; index < count; index += 1) {
        const button = inputs.nth(index);
        const label = ((await button.getAttribute('aria-label')) ?? '') + ' ' + ((await button.textContent()) ?? '') + ' ' + ((await button.getAttribute('value')) ?? '');
        if (SEARCH_PATTERN.test(label) && await button.isVisible().catch(() => false)) {
            await button.click();
            await page.waitForLoadState('domcontentloaded').catch(() => undefined);
            return true;
        }
    }
    return false;
}

async function extractRate(page) {
    const selector = '[data-testid*="price" i], [class*="price" i], [id*="price" i], [class*="rate" i], [id*="rate" i]';
    const locator = page.locator(selector);
    const focusedText = await locator.allTextContents();
    const focusedPrices = priceCandidates(focusedText.join('\n'));
    if (focusedPrices.length) return Math.min(...focusedPrices);
    const bodyText = await page.locator('body').innerText();
    const allPrices = priceCandidates(bodyText);
    return allPrices.length ? Math.min(...allPrices) : null;
}

await Actor.main(async () => {
try {
    const input = (await Actor.getInput()) ?? {};
    const startUrl = asUrl(input.startUrls?.[0]?.url ?? input.startUrls?.[0]);
    const stayDates = asStayDates(input.stayDates);
    const adults = Number.isInteger(input.adults) ? input.adults : 2;
    if (adults < 1 || adults > 10) throw new Error('adults must be between 1 and 10');
    let collectedResults = 0;

    const crawler = new PlaywrightCrawler({
        maxRequestsPerCrawl: 1,
        maxConcurrency: 1,
        maxRequestRetries: 0,
        requestHandlerTimeoutSecs: 90,
        launchContext: { launchOptions: { headless: true } },
        async requestHandler({ page, request }) {
            // PlaywrightCrawler already performed the sole navigation for this run.
            await page.waitForTimeout(1_000);
            let adultsSet = false;
            for (const checkIn of stayDates) {
                const checkOut = nextDate(checkIn);
                const checkInSet = await fillFirstVisible(page, DATE_SELECTORS.checkIn, checkIn);
                const checkOutSet = await fillFirstVisible(page, DATE_SELECTORS.checkOut, checkOut);
                adultsSet = adultsSet || await setAdultCount(page, adults);
                const submitted = (checkInSet || checkOutSet || adultsSet) ? await submitAvailabilitySearch(page) : false;
                await page.waitForTimeout(1_000);

                const bodyText = await page.locator('body').innerText();
                const nightlyPrice = await extractRate(page);
                const isFullyBooked = nightlyPrice === null && OTA.soldOutPattern.test(bodyText);
                if (nightlyPrice === null && !isFullyBooked) {
                    log.warning('No rate result was detected', {
                        finalUrl: page.url(),
                        title: await page.title(),
                        dateControls: { checkIn: checkInSet, checkOut: checkOutSet, adults: adultsSet, submitted },
                        textPreview: bodyText.replaceAll(/\s+/g, ' ').slice(0, 500),
                    });
                    throw new Error('No standard JPY availability result was found. Confirm the property URL and date-control selectors.');
                }
                await Actor.pushData({
                    ota: OTA.key,
                    propertyUrl: startUrl,
                    finalUrl: page.url(),
                    checkIn,
                    checkOut,
                    adults,
                    currency: 'JPY',
                    nightlyPrice,
                    isFullyBooked,
                    availability: isFullyBooked ? 'sold_out' : 'available',
                    dateControlsDetected: { checkIn: checkInSet, checkOut: checkOutSet, adults: adultsSet, submitted },
                    collectedAt: new Date().toISOString(),
                });
                collectedResults += 1;
            }
        },
    });
    await crawler.run([{ url: startUrl }]);
    if (collectedResults !== stayDates.length) throw new Error('The property page did not yield every requested rate result');
} catch (error) {
    log.error(`Rate collection failed: ${error.message}`);
    throw error;
}
});
