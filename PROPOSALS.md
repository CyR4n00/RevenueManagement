# Future Improvement Proposals for Revenue Assistant MVP

## 1. Data Granularity
* **Room Type & Meal Plan Filtering:** Currently, the system uses the Best Available Rate (BAR) across any room type. We should allow selecting and comparing specific room types (e.g., Double vs. Twin) and meal plans (e.g., Breakfast Included) to get more accurate competitive pricing.

## 2. Market Data Sourcing
* **External Scraping Services:** The local scraper `scraper.py` is a mocked stub that simulates data extraction due to OTA anti-bot protections. The production architecture should be updated to utilize external data scraping services such as Apify or Lighthouse to gather actual real-time pricing data reliably, without risking IP bans.

## 3. User Interface (UI) Enhancements
* **Price History Graphs:** Replace or augment the existing "Revenue Calendar" with interactive line graphs to visualize pricing trends over time.
* **Revenue Impact Calculation:** Add a module to calculate and display the estimated financial impact of adjusting prices based on the AI's recommendations.

## 4. Export Features
* **PDF & Extended CSV Export:** Provide detailed reports in PDF format for management meetings, alongside the current CSV export functionality.
