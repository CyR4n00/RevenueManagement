# Revenue Assistant MVP

A local B2B demo application functioning as an AI marketing tool specialized for the travel and accommodation industry.

## Overview

Based on user feedback, this MVP acts as a decision-support tool rather than just a pricing automation tool (or a site controller). It focuses on:
1. **Trend & Competitor Visualization (Visual Revenue Calendar):** Allowing users to understand area trends and competitor pricing movements at a glance.
2. **Decision-Making Support (Automated Recommendations):** Reducing the cognitive load of pricing decisions by proposing actions based on real-time market data.
3. **Competitor Data Analysis:** Simulating OTA scraping to capture competitor pricing and sellouts.
4. **Push Notifications:** Alerting low-IT-literacy operators via mock LINE/Email integrations only when specific thresholds are breached.

*Note: Automatic price reflection (direct integration with site controllers) is positioned as a higher-level, future feature.*

## Setup & Running

This is designed to run locally for sales pitches.

### Prerequisites

- Python 3.9+
- Node.js & `pnpm` (Must use `pnpm`, not `npm`)

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
