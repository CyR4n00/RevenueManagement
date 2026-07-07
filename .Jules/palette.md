## 2026-07-07 - [Addressing common React Warning with select element]
**Learning:** When using the `<select>` element in React, attempting to set a default value using the `selected` attribute on an `<option>` tag will raise a console warning. React prefers uncontrolled or controlled `<select>` tags by passing a `value` or `defaultValue` prop directly to the `<select>`.
**Action:** Always refactor `<option selected>` to `<select defaultValue="...">` to clean up console warnings and adhere to React standards.
