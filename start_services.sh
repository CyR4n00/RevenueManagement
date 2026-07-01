#!/bin/bash
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000 &
cd frontend && pnpm start &
