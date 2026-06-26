## 2024-05-18 - [Ensure correct ARIA toggling]
**Learning:** For a toggle button that controls a panel to be fully accessible, it is critical to ensure it uses `aria-expanded` with the current toggle state, and `aria-controls` pointing to the id of the panel it controls, so screen readers can correctly associate the toggle with the content that opens/closes.
**Action:** When implementing custom toggle panels, always bind `aria-expanded={isOpen}` on the button and pair it with `aria-controls="panel-id"` while giving the target panel `id="panel-id"`.
