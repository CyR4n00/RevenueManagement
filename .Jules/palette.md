## 2025-01-01 - [Accessibility & UX Form handling in React]
 **Learning:** React issues a warning when using the `selected` attribute directly on `<option>` elements in uncontrolled components, recommending `defaultValue` on the parent `<select>` instead. Further, modal dialogs must always include basic keyboard accessibility, such as an `Escape` keydown listener to close the modal, and an `aria-label` for icon-only close buttons.
 **Action:** Refactored React dropdown components to use `defaultValue`. Bound an event listener to `document` to listen for "Escape" to safely dismiss overlays, and added `aria-label="閉じる"` (Japanese for 'Close') on the X button icon.

## 2025-01-01 - [Testing Real API Workflows with Axios]
 **Learning:** When a React application relies on external API calls (`axios`), the unit test suite (`jsdom`) should not trigger actual network requests as it will throw "Network Error" when backend is unreachable or not configured for the test environment.
 **Action:** Explicitly mock API calls using `jest.mock('axios')` and provide appropriate mock resolved values reflecting expected responses before rendering components in `App.test.tsx`.
