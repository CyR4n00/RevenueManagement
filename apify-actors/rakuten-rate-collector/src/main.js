import { Actor } from 'apify';
import { CheerioCrawler, log } from 'crawlee';

const OTA = {
    key: 'rakuten',
    name: 'Rakuten Travel',
    allowedHosts: ['travel.rakuten.co.jp'],
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

function rakutenPropertyId(value) {
    const url = new URL(value);
    const match = url.pathname.match(/\/HOTEL\/(\d+)(?:\/|$)/i)
        ?? url.pathname.match(/\/hotelinfo\/(?:plan|room)\/(\d+)(?:\/|$)/i);
    if (!match) throw new Error('The Rakuten Travel property ID could not be read from the URL');
    return match[1];
}

function buildPlanUrl(propertyUrl, checkIn, checkOut, adults) {
    const propertyId = rakutenPropertyId(propertyUrl);
    const arrival = new Date(`${checkIn}T00:00:00Z`);
    const departure = new Date(`${checkOut}T00:00:00Z`);
    const url = new URL(`https://hotel.travel.rakuten.co.jp/hotelinfo/plan/${propertyId}`);
    const values = {
        f_flg: 'PLAN',
        f_static: '1',
        f_sort: 'minNo',
        f_heya_su: '1',
        f_otona_su: String(adults),
        f_s1: '0',
        f_s2: '0',
        f_y1: '0',
        f_y2: '0',
        f_y3: '0',
        f_y4: '0',
        f_nen1: String(arrival.getUTCFullYear()),
        f_tuki1: String(arrival.getUTCMonth() + 1),
        f_hi1: String(arrival.getUTCDate()),
        f_nen2: String(departure.getUTCFullYear()),
        f_tuki2: String(departure.getUTCMonth() + 1),
        f_hi2: String(departure.getUTCDate()),
    };
    for (const [key, value] of Object.entries(values)) url.searchParams.set(key, value);
    return url.toString();
}

function priceCandidates(text) {
    const candidates = [];
    for (const match of text.matchAll(/(?:¥|￥)\s*([\d,]+)/g)) candidates.push(match[1]);
    for (const match of text.matchAll(/([\d,]+)\s*円/g)) candidates.push(match[1]);
    return candidates
        .map((value) => Number.parseInt(value.replaceAll(',', ''), 10))
        .filter((value) => Number.isFinite(value) && value >= 3_000 && value <= 1_000_000);
}

function structuredRate($) {
    const scriptText = $('script').text();
    const matches = [...scriptText.matchAll(/sumTotalChargeTaxInclusive"\s*:\s*(\d+)/g)];
    if (!matches.length) return { detected: false, price: null };
    const prices = matches
        .map((match) => Number.parseInt(match[1], 10))
        .filter((value) => Number.isFinite(value) && value >= 3_000 && value <= 1_000_000);
    return { detected: true, price: prices.length ? Math.min(...prices) : null };
}

function normaliseDigits(value) {
    return value.replace(/[０-９]/g, (digit) => String(digit.charCodeAt(0) - 0xFEE0));
}

function extractAvailabilitySignal($, bodyText, nightlyPrice, isFullyBooked) {
    const inventorySelector = '[data-testid*="availability" i], [class*="stock" i], [class*="remain" i], [class*="vacan" i], [aria-label*="残"], [title*="残"]';
    const inventoryText = $(inventorySelector).text();
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

function extractRate($) {
    const content = $('body').clone();
    content.find('form, select, option, script, style, noscript').remove();
    const allPrices = priceCandidates(content.text());
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

    const crawler = new CheerioCrawler({
        maxRequestsPerCrawl: stayDates.length,
        maxConcurrency: 5,
        maxRequestRetries: 0,
        requestHandlerTimeoutSecs: 90,
        async requestHandler({ $, request }) {
            const checkIn = request.userData.checkIn;
            const checkOut = nextDate(checkIn);
            // Rakuten's readonly date picker can leave an overlay open and
            // intercept the checkout click. The public plan URL accepts the
            // same dates as query parameters, so every request is deterministic
            // and does not depend on fragile calendar UI interactions.
            const bodyText = $('body').text();
            const structured = structuredRate($);
            const nightlyPrice = structured.detected ? structured.price : extractRate($);
            const isFullyBooked = nightlyPrice === null
                && (structured.detected || OTA.soldOutPattern.test(bodyText));
            const availabilitySignal = extractAvailabilitySignal($, bodyText, nightlyPrice, isFullyBooked);
            if (nightlyPrice === null && availabilitySignal.status === 'unknown') {
                log.warning('No rate result was detected', {
                    finalUrl: request.loadedUrl ?? request.url,
                    title: $('title').text(),
                    dateControls: { directQuery: true },
                    textPreview: bodyText.replaceAll(/\s+/g, ' ').slice(0, 500),
                });
                throw new Error('No standard JPY availability result was found. Confirm the property URL and date-control selectors.');
            }
            await Actor.pushData({
                ota: OTA.key,
                propertyUrl: startUrl,
                finalUrl: request.loadedUrl ?? request.url,
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
                dateControlsDetected: { directQuery: true },
                collectedAt: new Date().toISOString(),
            });
            collectedResults += 1;
        },
    });
    await crawler.run(stayDates.map((checkIn) => ({
        url: buildPlanUrl(startUrl, checkIn, nextDate(checkIn), adults),
        uniqueKey: `${startUrl}::${checkIn}`,
        userData: { checkIn },
    })));
    if (collectedResults === 0) throw new Error('The property page did not yield any requested rate result');
    if (collectedResults !== stayDates.length) {
        log.warning('The run completed with partial results; missing dates will be retried', {
            requested: stayDates.length,
            collected: collectedResults,
        });
    }
} catch (error) {
    log.error(`Rate collection failed: ${error.message}`);
    throw error;
}
});
