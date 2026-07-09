## 2026-07-09 - [Accessible Async Loading States]
**Learning:** Utilizing a full-content wrapper with opacity transition (e.g., opacity-50 pointer-events-none) and aria-busy={isLoading} provides immediate, accessible feedback without causing layout shifts.
**Action:** Applied this pattern to the main dashboard in App.tsx to improve user experience during data fetching.
