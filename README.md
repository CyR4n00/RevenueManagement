# Revenue Assistant MVP

A local B2B demo application focused on competitor price tracking and revenue recommendations.

## Overview

Based on user feedback, this MVP focuses strictly on:
1. **Competitor Data Analysis:** Simulating OTA scraping to capture competitor pricing and sellouts.
2. **Visual Revenue Calendar:** Displaying up/down pricing trends among competitors to quickly evaluate the market.
3. **Automated Recommendations:** Proposing price actions based on real-time changes rather than complex, opaque ML models.
4. **Push Notifications:** Alerting low-IT-literacy operators via mock LINE/Email integrations only when specific thresholds are breached.

## Setup & Running

This is designed to run locally for sales pitches.

### Prerequisites

- Python 3.9+
- Node.js & `pnpm` (Must use `pnpm`, not `npm`)

### Configuration

If you want to test the Apify scraper integration, export your API key before starting the backend:
```bash
export APIFY_API_KEY="your_api_key_here"
```

### Starting the Application

You can use the provided start scripts which boot both the backend and frontend simultaneously.

**Mac / Linux:**
```bash
./start.sh
```

**Windows:**
```bat
start.bat
```

The frontend will be available at `http://localhost:3000`.
The backend API will be available at `http://localhost:8000`.

## Architecture Details

- **Backend:** FastAPI, SQLAlchemy, Local SQLite database (`revenue_assistant.db`)
- **Frontend:** React, TypeScript, Tailwind CSS, Create React App
- **Scraping:** Currently a local Python stub (`scraper.py`) that returns deterministic, simulated market data for demonstration without risking IP bans.
- **Future Production Path:** See `DB_ARCHITECTURE.md` for Supabase migration and `API_RESEARCH.md` for Apify integration.
