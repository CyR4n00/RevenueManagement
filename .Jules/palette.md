## 2024-06-12 - Modal Accessibility Pattern
**Learning:** Icon-only close buttons in modals (like `&times;`) lack context for screen reader users and can be hard to discover keyboard alternatives for.
**Action:** Always add `aria-label` and `title` to icon-only buttons, and pair modals with an `Escape` key event listener for keyboard dismissal.
