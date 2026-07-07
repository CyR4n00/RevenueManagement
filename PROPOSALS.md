# Proposals for Future Development

This document outlines proposed future improvements and optimizations to the Revenue Assistant MVP based on architectural research and UX findings.

## UI / UX Improvements
- **Loading States:** An `isLoading` state was added to the main App component, providing immediate visual feedback to the user while data is fetched.
- **Accessibility Enhancements:** Ensure keyboard navigability via `focus-visible` states and explicitly associated `<label>` and `<input>` fields.
- **Price History Popups:** Introduce an interactive popup/modal when clicking on a price in the Revenue Calendar to view its historical trend over the last 30 days.
- **Room Type Filtering:** Expand the Settings Panel to allow selection of specific room types and plan types (e.g., "Standard Twin", "Breakfast Included") instead of defaulting to the cheapest Best Available Rate (BAR).

## Architecture & Integration Optimizations
- **Export Capabilities:** Allow exporting the generated pricing matrix and AI recommendations to PDF/CSV for distribution among hotel staff.
- **Revenue Impact Calculation:** Attempt to project estimated revenue impacts when suggested prices are adopted vs. maintaining current pricing.
- **External API Integration:** While the MVP utilizes a direct fallback approach for OTA scraping, production should migrate to Apify Actors (already stubbed) or official Lighthouse APIs to prevent IP blocking and guarantee data fidelity.
- **Database Scaling:** Follow `DB_ARCHITECTURE.md` to migrate from local SQLite to Supabase (PostgreSQL) leveraging Row Level Security (RLS) for multi-tenant isolation.
