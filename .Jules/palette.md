
## 2024-06-24 - React Form Accessibility and State
**Learning:** In React, using `selected` on `<option>` tags within a `<select>` triggers warnings and is discouraged. Additionally, for low-IT literacy users, explicit mapping of labels using `htmlFor` and `id` ensures proper target areas and screen reader compatibility.
**Action:** Always utilize the `defaultValue` attribute on the parent `<select>` element to set the initial choice. Consistently connect `<label>` elements to their interactive targets via `htmlFor` matching the target's `id`. For inputs without a label, explicitly define `aria-label`.
