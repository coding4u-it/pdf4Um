# Localhost PDF API Boundary

For a single-process Java PDF tool, a JDK loopback HTTP server can expose the existing PDFBox domain operations without introducing a production web framework.

## What Happened

In `pdf4Um` task t4, the server used `HttpServer` bound explicitly to `127.0.0.1`, a bounded multipart parser, and one temporary directory per upload request. A new controller/model instance per request kept the existing PDFBox methods isolated; renamed files and random-mode CSV were generated as copies under the workspace. HTTP integration tests exercised all five operations.

## Takeaway

Keep the HTTP boundary thin: upload bytes (never client filesystem paths), validate the PDFs before processing, write output only inside request-owned temporary storage, stream downloads before cleanup, and avoid retaining controller/password/file-selection state. Serve only explicitly allowlisted static resources from the same origin. Document any upload-size or file-count cap for the UI/client.

## History
- 2026-10-24 (pdf4Um/t4): initial
