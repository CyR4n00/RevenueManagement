## 2024-05-18 - Accessibility Improvements in React
**Learning:** React requires specific attributes for accessibility (a11y). For example, `defaultValue` on `<select>` instead of `selected` on `<option>`, explicitly linking `<label>` and `<input>` using `htmlFor` and `id`, and adding `aria-label` for icon-only buttons.
**Action:** Always verify a11y patterns (like `focus-visible` classes in Tailwind) in UI components to enhance UX.
## 2024-05-18 - pnpm script issues
**Learning:** Newer pnpm versions may aggressively block postinstall scripts (like `core-js`), leading to failures.
**Action:** Use `pnpm install --ignore-scripts` in CI/start scripts to bypass this issue if the scripts are not strictly required for the build.
