# Future Improvement Proposals for MVP

This document tracks potential future enhancements for the Revenue Assistant MVP to provide further value to our users and increase the product's depth beyond the current demonstration setup.

## 1. Room Type & Plan Filtering
*   **Current State:** The MVP focuses on tracking the most accessible overall price metric—Best Available Rate (BAR)—without considering room types or inclusion of meals.
*   **Proposal:** Implement detailed scraping or API data acquisition (e.g., using Apify or Lighthouse) to support granular benchmarking. Users will be able to select specific configurations (e.g., "Standard Twin", "Breakfast Included") and monitor competitor pricing aligned with those exact filters.

## 2. Price History & Fluctuation Popups
*   **Current State:** The Revenue Calendar displays daily pricing and highlights the difference strictly from the previous day.
*   **Proposal:** Introduce interactive UI elements where users can click on a specific price cell to view a tooltip or popup modal charting the history of how that specific day's price changed over time (e.g., "Price was 12,000 Yen 30 days out, dropped to 10,000 Yen 7 days out").

## 3. PDF / CSV Export Enhancements
*   **Current State:** Currently supports basic CSV exporting intended for rudimentary integration with Site Controllers.
*   **Proposal:**
    *   Expand CSV export configurations to directly map onto major domestic Japanese Site Controllers' formats (e.g., Neppan, TEMAIRAZU) for frictionless bulk uploads.
    *   Add a PDF export feature to generate daily or weekly visual reports summarizing competitor trends, alerts triggered, and AI pricing recommendations for internal hotel stakeholder meetings.

## 4. Revenue Impact Calculation
*   **Current State:** Recommendations suggest a new price based on competitor movements and market average but do not quantify the business impact.
*   **Proposal:** Allow users to input their total room count and expected occupancy. Provide estimated "Revenue Impact" metrics alongside recommendations (e.g., "Raising the price to 15,000 Yen is estimated to increase daily revenue by 50,000 Yen assuming a 5% drop in occupancy").
