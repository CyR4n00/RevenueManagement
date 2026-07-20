# Jalan Best Available Rate Collector

Private Actor used only by Revenue Assistant for the approved Jalan collection
flow. It accepts one property URL, a controlled list of one-night stays, and
guest count, then writes one standard result per stay date to the default
dataset.

The Actor deliberately uses a single browser flow with no proxy rotation,
captcha handling, login, retry loop, or scraping of unrelated pages. The
application starts no more than two Actor runs per facility per day under the
written approval held by the service owner.

## Dataset contract

Successful runs write one item with `nightlyPrice` (JPY) or, when a clear sold
out signal is present and no price is available, `isFullyBooked: true`.
`Revenue Assistant` consumes these two fields only.
