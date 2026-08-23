import { Actor } from 'apify';
import { PlaywrightCrawler, log } from 'crawlee';

const OTA = {
    key: 'jalan',
    name: 'Jalan',
    allowedHosts: ['www.jalan.net', 'jalan.net'],
    soldOutPattern: /(満室|空室なし|ご予約いただけません|予約できません|該当するプランはありません|sold\s*out|no\s*availability)/i,
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
    if (!Array.isArray(values) || values.length < 1 || values.length > 90) {
        throw new Error('stayDates must contain between 1 and 90 dates');
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

function normaliseDigits(value) {
    return value.replace(/[０-９]/g, (digit) => String(digit.charCodeAt(0) - 0xFEE0));
}

async function extractAvailabilitySignal(page, bodyText, nightlyPrice, isFullyBooked) {
    const inventorySelector = '[data-testid*="availability" i], [class*="stock" i], [class*="remain" i], [class*="vacan" i], [aria-label*="残"], [title*="残"]';
    const inventoryText = (await page.locator(inventorySelector).allTextContents().catch(() => [])).join(' ');
    const roomCounts = [...normaliseDigits(bodyText).matchAll(/(?:残り|あと|残室)\s*(\d+)\s*室/g)]
        .map((match) => Number.parseInt(match[1], 10))
        .filter((value) => Number.isInteger(value) && value >= 0 && value <= 10_000);
    const remainingRooms = roomCounts.length ? Math.min(...roomCounts) : null;
    if (isFullyBooked || remainingRooms === 0) {
        return { status: 'sold_out', remainingRooms, source: remainingRooms === 0 ? 'explicit_count' : 'inferred' };
    }
    if (remainingRooms !== null) {
        return { status: remainingRooms <= 3 ? 'limited' : 'available', remainingRooms, source: 'explicit_count' };
    }
    if (/(残りわずか|残室わずか|空室わずか)/i.test(bodyText) || /(^|\s)[△▲](\s|$)/.test(inventoryText)) {
        return { status: 'limited', remainingRooms: null, source: 'symbol' };
    }
    if (/(^|\s)[×✕](\s|$)/.test(inventoryText)) {
        return { status: 'sold_out', remainingRooms: null, source: 'symbol' };
    }
    if (/(^|\s)[○◯](\s|$)/.test(inventoryText)) {
        return { status: 'available', remainingRooms: null, source: 'symbol' };
    }
    return { status: nightlyPrice === null ? 'unknown' : 'available', remainingRooms: null, source: nightlyPrice === null ? 'unknown' : 'inferred' };
}


async function submitJalanSearch(page, checkIn, adults) {
    const form = page.locator('form[action*="uww3101.do"]').first();
    if (!await form.count()) return false;
    const [year, month, day] = checkIn.split('-');
    await Promise.all([
        page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 30_000 }),
        form.evaluate((element, values) => {
            const setValue = (name, value) => {
                const field = element.querySelector(`[name="${name}"]`);
                if (field) field.value = value;
            };
            setValue('stayYear', values.year);
            setValue('stayMonth', values.month);
            setValue('stayDay', values.day);
            setValue('stayCount', '1');
            setValue('dateUndecided', '0');
            setValue('roomCount', '1');
            setValue('adultNum', String(values.adults));
            setValue('roomCrack', `${values.adults}${'0'.repeat(5)}`);
            HTMLFormElement.prototype.submit.call(element);
        }, { year, month, day, adults }),
    ]);
    return true;
}

async function fillFirstVisible(page, selectors, value, calendarAlreadyOpen = false) {
    for (const selector of selectors) {
        const locator = page.locator(selector).first();
        if (await locator.count() && await locator.isVisible().catch(() => false)) {
            if (await locator.getAttribute('readonly') !== null) {
                const calendarDay = page.locator(`[data-time="${Date.parse(`${value}T00:00:00Z`)}"]:not(.not-available)`).first();
                if (!calendarAlreadyOpen || !await calendarDay.isVisible().catch(() => false)) {
                    await page.keyboard.press('Escape').catch(() => undefined);
                    await locator.click({ timeout: 5_000 });
                    await page.waitForTimeout(300);
                }
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

async function extractRate(page, adults) {
    const totals = priceCandidates((await page.locator('.p-searchResultItem__total').allTextContents()).join('\n'));
    if (totals.length) return Math.min(...totals);
    const perPerson = priceCandidates((await page.locator('.p-searchResultItem__perPerson').allTextContents()).join('\n'));
    return perPerson.length ? Math.min(...perPerson) * adults : null;
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
        // One independent page per stay date keeps a 90-day collection below
        // the Actor run timeout. Three concurrent pages is intentionally
        // conservative toward the approved OTA while avoiding the former
        // ten-minute sequential timeout.
        maxRequestsPerCrawl: stayDates.length,
        maxConcurrency: 3,
        maxRequestRetries: 0,
        requestHandlerTimeoutSecs: 90,
        launchContext: { launchOptions: { headless: true } },
        async requestHandler({ page, request }) {
            const checkIn = request.userData.checkIn;
            const checkOut = nextDate(checkIn);
            await page.waitForTimeout(300);
            const submitted = await submitJalanSearch(page, checkIn, adults);
            await page.waitForTimeout(300);

            const bodyText = await page.locator('body').innerText();
            const nightlyPrice = await extractRate(page, adults);
            const isFullyBooked = nightlyPrice === null && OTA.soldOutPattern.test(bodyText);
            const availabilitySignal = await extractAvailabilitySignal(page, bodyText, nightlyPrice, isFullyBooked);
            if (nightlyPrice === null && availabilitySignal.status === 'unknown') {
                log.warning('No rate result was detected', {
                    finalUrl: page.url(),
                    title: await page.title(),
                    dateControls: { formSubmitted: submitted, adults },
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
                isFullyBooked: availabilitySignal.status === 'sold_out',
                availability: availabilitySignal.status,
                availabilityStatus: availabilitySignal.status,
                remainingRooms: availabilitySignal.remainingRooms,
                availabilitySource: availabilitySignal.source,
                dateControlsDetected: { formSubmitted: submitted, adults },
                collectedAt: new Date().toISOString(),
            });
            collectedResults += 1;
        },
    });
    await crawler.run(stayDates.map((checkIn) => ({
        url: startUrl,
        uniqueKey: `${startUrl}::${checkIn}`,
        userData: { checkIn },
    })));
    if (collectedResults !== stayDates.length) throw new Error('The property page did not yield every requested rate result');
} catch (error) {
    log.error(`Rate collection failed: ${error.message}`);
    throw error;
}
});
