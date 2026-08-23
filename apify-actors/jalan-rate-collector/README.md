# Jalan Best Available Rate Collector

Private Actor used only by レベナビ for the approved Jalan collection
flow. It accepts one property URL, a controlled list of one-night stays, and
guest count, then writes one standard result per stay date to the default
dataset.

The Actor deliberately uses three concurrent browser pages with no proxy rotation,
captcha handling, login, retry loop, or scraping of unrelated pages. The
application starts no more than two Actor runs per facility per day under the
written approval held by the service owner.

## Dataset contract

Successful runs write `nightlyPrice` (JPY), `availabilityStatus`, the optional
explicit `remainingRooms`, and `availabilitySource`. When a clear sold-out
signal is present without a price, `isFullyBooked` is true. A room count is
never invented when the OTA does not display one.
