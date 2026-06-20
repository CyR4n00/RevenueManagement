
## 2023-10-27 - [Add ARIA labels to Modal/Panel controls]
**Learning:** Icon-only buttons (like `&times;` for closing panels) require explicit `aria-label`s for screen readers, and should use `focus-visible:ring-2 focus-visible:outline-none` styles for keyboard navigation visibility. Adding `id` and `htmlFor` to form elements like `<select>` improves accessibility and user experience.
**Action:** Always verify that all icon-only buttons in modals and panels have accessible labels and keyboard focus states. Use `defaultValue` instead of `selected` on options for React form controls.
