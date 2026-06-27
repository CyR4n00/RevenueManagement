## 2024-05-24 - Explicit Form Labels & Controlled Selects
**Learning:** React throws warnings and screen readers fail to associate form fields properly when labels implicitly wrap inputs or select options use the `selected` attribute. Explicit `htmlFor` bindings and using `defaultValue` on the `<select>` root element is critical for both accessibility and modern React compliance.
**Action:** Always explicitly bind `<label htmlFor="id">` to `<input id="id">` or `<select id="id">`. Move `selected` attributes to `defaultValue="value"` on the parent `<select>`.
