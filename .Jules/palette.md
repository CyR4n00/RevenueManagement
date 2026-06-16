## 2024-05-18 - Ensure robust API data fetching
 **Learning:** In client prototype setups, unhandled API rejections severely break the frontend rendering and UX, confusing non-technical reviewers if the backend is down.
 **Action:** Wrap all asynchronous data fetches (`App.tsx` -> `fetchData()`) in robust try-catch blocks and provide clear, polite Japanese error messages in the UI explaining that the server is unreachable.
