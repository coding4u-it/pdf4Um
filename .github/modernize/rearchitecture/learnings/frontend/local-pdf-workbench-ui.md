# Local PDF Workbench UI

For a small localhost-only Java file-processing app, a dependency-free same-origin HTML/CSS/JavaScript workbench can use multipart uploads and download responses without introducing a separate frontend runtime.

## What Happened

In `pdf4Um` task t5, the Java server already exposed an allowlisted set of three static resources and multipart operation routes. The browser implementation used native labeled controls, a single explicit selected-file list, `FormData` uploads, Blob downloads, and `textContent` for filenames. Headless browser interaction checks exposed a mismatched split-pages error element ID; aligning the associated label/control/error IDs made inline validation and `aria-invalid` state work.

In `pdf4Um` task t5.1, review showed the server's JSON error key and the browser's expected key differed, a focus helper was too narrowly scoped for the generic 400 path, and removing the final list item could discard focus. The UI now reads `error` first (with `message` fallback), queues focus until busy controls are restored, and routes result-state visuals through one `data-state` helper.

## Takeaway

When building UI on a small Java static-resource server, keep the asset paths allowlisted and match each multipart field and error-response property exactly to the server contract. Build dynamic filename content with text nodes, keep the operation inputs native and labeled, and test field-level validation in a real browser rather than relying only on static HTML checks. Queue focus changes until disabled controls are restored; after removing list items, focus the next item, previous item, or the input control when the list is empty. Keep result icon and color state driven by a single result-state attribute.

## History
- 2026-10-24 (pdf4Um/t5): initial
- 2026-10-24 (pdf4Um/t5.1): documented API error-field alignment, busy-state focus handling, and explicit result-state visuals.
