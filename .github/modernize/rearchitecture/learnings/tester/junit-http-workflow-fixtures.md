# JUnit HTTP Workflow Fixtures

For Java PDF applications using the JDK HTTP server, JUnit 4 and PDFBox can exercise real multipart routes using temporary loopback ports and generated in-memory PDFs without adding browser-test dependencies.

## What Happened

In `pdf4Um` task t10, workflow regression coverage used a shared JUnit base for ephemeral-server startup/cleanup, multipart HTTP posting, synthetic PDF creation, and ZIP inspection. Tests verified output content by loading the returned PDF bytes with PDFBox. Browser journeys were separately exercised through integrated Playwright.

## Takeaway

Use generated in-memory PDF fixtures and an ephemeral `127.0.0.1` server for deterministic endpoint workflows. Verify response bytes and semantic content rather than only HTTP status. Keep browser tests separate for rendered UI interactions and state.

## History
- 2026-10-24 (pdf4Um/t10): initial
