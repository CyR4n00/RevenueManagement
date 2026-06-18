## 2026-06-18 - [Handling Dynamic Text and Data Formatting in React/FastAPI]
**Learning:** When text descriptions include embedded dynamic formatted values (e.g., rounded prices), ensure formatting operations (like `round()`) occur *before* the variable is interpolated into string templates to prevent UX mismatches.
**Action:** Reordered backend logic in `main.py` so the suggested price is rounded before building the reasoning text.
