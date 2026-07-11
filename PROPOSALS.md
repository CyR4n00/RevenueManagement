# Revenue Assistant - Future Proposals

This document outlines potential improvements and feature additions for the Revenue Assistant project beyond the current MVP phase.

## 1. Real Webhook Integrations
**Current State:** The external notifications (LINE, Email) are mocked or depend on local configuration stubs in the `notifier.py` service.
**Proposal:** Implement robust webhook integrations for popular messaging platforms used by operators in Japan (e.g., Slack, Chatwork, LINE Business). This involves creating a secure settings UI to store OAuth tokens and integrating an asynchronous job queue (e.g., Celery or Redis Queue) to handle notification delivery without blocking the main API thread.

## 2. Flexible Room Type and Meal Plan Tracking
**Current State:** The competitor scraping relies on a naive fallback and essentially tracks the lowest "Best Available Rate" (BAR).
**Proposal:** Introduce structured data tracking for specific room types (e.g., Single, Twin, Suite) and meal plans (e.g., Room Only, Breakfast Included). This will require:
- Expanding the `DBCompetitorPrice` model to include `room_type` and `meal_plan` columns.
- Updating the scraper engine (e.g., via Apify integration) to extract and categorize detailed pricing data.
- Enhancing the Revenue Calendar UI to allow filtering by room type and meal plan.

## 3. Dynamic Date Range Selection
**Current State:** The dashboard displays a fixed 7-day window starting from the selected date.
**Proposal:** Allow users to define custom date ranges (e.g., 14 days, 30 days, or a specific month).
- Update the `GET /market_data` endpoint to accept an `end_date` parameter instead of just `days`.
- Introduce a date-picker component in the React frontend that supports range selection (e.g., `react-datepicker`).

## 4. Multi-tenant User Management
**Current State:** The system assumes a single tenant (facility) running locally on a SQLite database.
**Proposal:** As part of the migration to Supabase (PostgreSQL), implement full user authentication and multi-tenancy.
- Use Supabase Auth for user login and session management.
- Introduce `tenant_id` across all database models to isolate data between different hotel operators.
- Implement Role-Based Access Control (RBAC) to differentiate between regular staff and administrators within a single facility.

## 5. Automated PMS / Site Controller Integration
**Current State:** The application generates a CSV file intended for manual upload to Site Controllers like Neppan.
**Proposal:** Develop direct, secure 2-way API connections to major PMS and Site Controllers.
- Allow the AI to not just suggest, but automatically push price updates (within the defined guardrails) directly to the Site Controller.
- Require extensive testing and certification with PMS providers.

## 6. Historical Data & Analytics Dashboard
**Current State:** The dashboard only shows current and short-term future pricing data.
**Proposal:** Build a dedicated analytics view that visualizes pricing trends and occupancy rates over the past 6-12 months.
- Implement charts (using libraries like `recharts`) showing historical price changes versus competitor averages.
- Track the actual conversion/revenue impact of the AI's suggested price changes over time.
