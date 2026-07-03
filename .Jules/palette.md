
## 2024-05-18 - Accessibility improvements for inputs and selects
**Learning:** React logs a warning when `<option selected>` is used; instead, `<select defaultValue="value">` should be utilized for uncontrolled components. Also, explicit accessibility mappings via `htmlFor` on a `<label>` mapped to the corresponding `id` of an `<input>` are essential, especially when rendering lists or dynamic components (like mapped competitor configs or multiple checkboxes).
**Action:** Always ensure dynamic inputs in React lists receive unique IDs and explicit labels. Replace `selected` attributes in `<option>` tags with `defaultValue` on the parent `<select>` to adhere to React component standards and prevent warnings.
