# Future Improvement Proposals for Revenue Assistant

This document tracks planned feature enhancements and architecture improvements beyond the current MVP phase.

## 1. Advanced Competitor Benchmarking
- **Room Type & Plan Filtering:** Transition from tracking only the Best Available Rate (BAR) to scraping and comparing prices based on specific room types, meal inclusions (e.g., with/without breakfast), and cancellation policies.

## 2. Enhanced Data Visualization & Reporting
- **Price History Popups:** Implement interactive charts on the Revenue Calendar to show historical price trends for specific days/competitors over time.
- **Export Capabilities:** Allow exporting market data and revenue calendar views to PDF and CSV formats for offline analysis and reporting.

## 3. Revenue Impact & Analytics
- **Revenue Impact Calculation:** Integrate self-facility inventory data to estimate the potential revenue impact of following AI suggestions.
- **Machine Learning Integration:** Explore utilizing historical sales data alongside competitor trends to develop an internal ML model for deeper, personalized demand forecasting (rather than relying solely on immediate competitor rate changes).

## 4. Automation & Integration
- **Direct PMS / Site Controller Sync:** Evolve from a "Suggestion & Push Notification" model to a fully automated two-way API sync that directly updates the facility's Site Controller/PMS.

## 5. Technical Infrastructure (In Progress)
- **Database Migration:** Finalize the transition from local SQLite to a cloud-based Supabase (PostgreSQL) architecture, implementing Row Level Security (RLS) for multi-tenant data isolation.
- **Robust Scraping via Apify:** Replace the current local Python simulation fallback with commercial scraping APIs like Apify to circumvent OTA bot protections reliably.
