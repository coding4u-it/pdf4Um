## [t10] Validated PDF workflows in HTTP tests and browser
- Codebase/domain discoveries: the server can bind to an ephemeral port for in-process HTTP tests; route responses can be read back as PDFs/ZIPs; the browser app uses same-origin multipart uploads and Blob download links.
- Wrong assumptions and corrections: `getByLabel("Prefisso")` matched both the rename radio group and its text field; using `#rename-prefix` resolved the browser locator ambiguity. Local appmod browser launch lacked its cached Chromium, but integrated browser Playwright worked.
- Techniques/patterns worth reusing: generate small PDF fixtures with PDFBox; use a shared JUnit 4 support class for server lifecycle, multipart requests, and ZIP parsing; test merge order by extracted page text.
- Issues: no approved testing-strategy artifact or tester context/log/inbox existed before this task. No app defect found; report records the deviation and non-applicable auth/persistence checks.
- Learnings consumed: [(none)]
