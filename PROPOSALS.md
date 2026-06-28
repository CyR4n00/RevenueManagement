# Future Improvement Proposals for MVP

This document outlines proposals for future features and improvements to the Revenue Assistant MVP to enhance its capability to track competitor data and provide actionable revenue suggestions.

## 1. Room Type & Plan Filtering

**Problem:** Currently, the system only tracks the "Best Available Rate" (BAR), which might not give an accurate picture if a competitor's cheapest room is vastly different from ours (e.g., dormitory vs. private room).
**Proposal:** Update the database and scraper/API to track specific room types, plan types (e.g., breakfast included vs. room only), and cancellation policies. Allow users to configure which specific competitor plans they want to benchmark against their own plans.

## 2. Price History & Trends Popup

**Problem:** The current Revenue Calendar shows day-over-day changes, but it can be difficult to see long-term trends for a specific date (e.g., how the price for August 15th has evolved over the past month).
**Proposal:** Add a clickable popup or modal on the Revenue Calendar cells. Clicking a price would show a small line graph detailing the historical price changes for that specific check-in date over the last 30/60 days.

## 3. PDF/CSV Export Functionality

**Problem:** Hotel managers and operators often need to present pricing data and competitor analysis in weekly or monthly revenue meetings.
**Proposal:** Implement an "Export" button on the dashboard that allows users to download the Revenue Calendar and recent Alerts as a clean, formatted PDF report or as raw CSV data for further analysis in Excel.

## 4. Revenue Impact Calculation

**Problem:** AI price suggestions provide a recommended price, but don't quantify the potential business impact.
**Proposal:** Add a feature that estimates the "Revenue Impact" of accepting a price suggestion. For example, "By raising the price to ¥12,000 for the next 5 remaining rooms, estimated additional revenue is ¥10,000." This requires tracking the user's own inventory and incorporating it into the AI reasoning.

## 5. Machine Learning Enhancements

**Problem:** The current AI suggestion relies heavily on simple threshold rules based on current market averages.
**Proposal:** As historical data is accumulated (especially after moving to Supabase/PostgreSQL), begin training machine learning models to identify seasonal patterns, local event impacts, and booking velocity trends, moving towards predictive pricing rather than purely reactive pricing.