## 2025-02-18 - B2B Form Label Associations & React Select DefaultValue
**Learning:** React throws warnings and screen readers fail when `selected` is used on `<option>` tags inside `<select>` or when `<label>` tags are not explicitly associated with inputs via `htmlFor` and `id`. This is critical for accessibility and clean console in B2B dashboard apps with many form controls.
**Action:** Always use `defaultValue` on the `<select>` element itself instead of `selected` on the options. Always explicitly associate `<label>` elements with inputs using matching `htmlFor` and `id` attributes.
