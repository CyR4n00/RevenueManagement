## 2026-07-20 - Explicit Form Label Binding and Select defaultValue
**Learning:** React 19 / generic frontend accessibility requires explicit `htmlFor` and `id` bindings for proper screen reader support. `<select>` components using `selected` attribute on `<option>` throw React warnings and are less accessible than using `defaultValue` on the `<select>` itself.
**Action:** Always use `htmlFor` on `<label>` paired with `id` on `<input>`/`<select>`. Never use `selected` on options; always use `defaultValue` on the root `<select>` element.
