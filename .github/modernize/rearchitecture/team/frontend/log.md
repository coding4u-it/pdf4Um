## [t5] Implemented the browser-based PDF workbench
- Codebase/domain discoveries: The backend exposes only three allowlisted static assets and operation endpoints on the same origin; keep the browser API requests and packaged UI aligned to those routes. The server caps each request at 32 PDFs and 100 MiB.
- Wrong assumptions and corrections: The first split group-size validation pass had a mismatched `pages-error` element ID versus the JavaScript's expected `pages-per-part-error`; browser interaction checks found it and the IDs were aligned. Early assertion failures also included a test expectation error and a typo in an ad-hoc browser script; the final Chrome checks passed.
- Debugging dead-ends and what actually worked: The available helper browser launcher lacked its Chromium binary. The installed system Chrome worked headlessly, and local Chrome DevTools Protocol evaluation verified real page behavior without changing repository dependencies.
- Techniques/patterns worth reusing: Use native fieldsets/radios, textContent for filenames, explicit inline error IDs paired with `aria-describedby`, and an ordered keyboard-adjustable list for merge. Add a 32-file client-side cap that agrees with the server and map 413 responses to localized feedback.
- Learnings consumed: [architect/localhost-pdf-web-boundary]

## [t5.1] Fixed frontend error feedback and keyboard focus
- Codebase/domain discoveries: The Java API returns its JSON detail in `error`; frontend parsing should prefer that contract while tolerating `message` for older responses. An error response may be handled while the operation is busy, so focus must be queued until controls are re-enabled.
- Wrong assumptions and corrections: The generic 400 handler referenced a focus helper scoped only inside field validation; moving it to shared scope removes the fallback ReferenceError.
- Debugging dead-ends and what actually worked: Node.js is absent, but installed headless Chrome can execute the actual served JavaScript. CDP checks verified the generic 400 response, error-state styling, retained file selection, and keyboard focus without adding project dependencies.
- Techniques/patterns worth reusing: Track result presentation with a `data-state` attribute, choose the matching icon/color via one helper, and after deleting a list item focus the same index (next item), otherwise the previous item, or the picker when empty.
- Learnings consumed: [frontend/local-pdf-workbench-ui, ux/localhost-pdf-workbench]
