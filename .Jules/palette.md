## 2024-05-19 - Added ARIA label to Icon-only button
**Learning:** Found an icon-only close button (`&times;`) in `SettingsPanel` without an accessible name, making it invisible or confusing for screen reader users. Also lacking focus ring.
**Action:** Always verify that buttons containing only an icon or symbol have a descriptive `aria-label`. Apply keyboard focus styles using Tailwind (`focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400`).
