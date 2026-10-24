# t7 — Architecture Conformance and Loopback Review

## Verdict

**PASS with one low-severity client/server error-message mismatch.** The application conforms to the designed single-process Java/PDFBox boundary and is explicitly bound to IPv4 loopback. The current integration tests pass and directly assert the bound address.

## Review Evidence

- **Loopback-only binding — PASS.** `Pdf4UmWebServer` resolves the literal `127.0.0.1` and constructs its `HttpServer` socket with that address (`src/main/java/com/mycompany/pdf4um/web/Pdf4UmWebServer.java:45-50`). There is no configurable host/LAN bind. `Pdf4UmWebServerTest` asserts both loopback status and exact address (`src/test/java/com/mycompany/pdf4um/web/Pdf4UmWebServerTest.java:51-54`).
- **Boundary and runtime shape — PASS.** `Main` retains its existing FQCN, reads only the optional port property, starts the server, and installs a shutdown hook. UI resources are explicitly allowlisted and served from the same origin; API dispatch accepts only the five designed POST routes.
- **Request isolation — PASS.** Multipart data is bounded; each request gets a temporary workspace, the operation creates a fresh controller/model, and workspace cleanup is in a `finally` block. Uploads are reduced to sanitized PDF filenames, not treated as client paths.
- **Preserved domain operations — PASS.** The server delegates split, merge, rename-copy, encryption, and text extraction to the existing Java/PDFBox model/controller path. Endpoint tests exercise all five workflows and representative contract errors.
- **Browser/API request shape — PASS with finding below.** The browser submits same-origin multipart requests using the designed route names and fields and downloads the generated attachment. It does not request CORS or send client filesystem paths.

## Finding

### Error JSON property mismatch — Low

The server serializes failures as `{"error":"..."}` (`src/main/java/com/mycompany/pdf4um/web/Pdf4UmWebServer.java:370-380`), while the browser reads `body.message` (`src/main/resources/web/app.js:427-434`). Consequently the browser discards the server's error text; its 400-specific field mapping at `app.js:437-458` cannot distinguish those server validation messages and falls back to generic feedback. Status-specific handling for 413, 415, and 422 remains in place, and client-side checks cover the ordinary invalid form cases.

**Recommended correction:** align the JSON property on both sides (prefer reading `body.error` in the frontend if retaining the current server response shape). Add a focused negative-response/UI assertion for a server-side 400 to prevent regression.

## Test Results

- Command: `mvn -B test`
- Passed: 2
- Failed: 0
- Skipped: 0
- Failures: none.
- `Pdf4UmWebServerTest#bindsToLoopbackAndSupportsAllPdfWorkflows` passed, including exact `127.0.0.1` address assertions and successful responses for all five workflows.
- Maven emitted a warning that `maven-jar-plugin` has no pinned version; this did not affect the test result and is outside this review's scope.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t1-architect.md` — design decisions and implementation boundary.
- `.github/modernize/rearchitecture/artifacts/t4-backend.md` and `t4-backend-implementation.md` — backend implementation summary, runtime behavior, and test claims checked against source.
- `.github/modernize/rearchitecture/artifacts/t5-frontend.md` and `t5-frontend-batch-report.yaml` — browser workflow implementation and verification claims checked against source.

## Evidence Mapping

- `t1-architect.md#Key decisions` and `architecture_index.md#Runtime and request rules` → fixed loopback socket, same-origin route boundary, bounded uploads, request-local temporary workspace, and operation isolation → `Pdf4UmWebServer.java:45-54,141-166`; `Pdf4UmWebServerTest.java:51-54`; `mvn -B test`.
- `t4-backend-implementation.md#Server and route boundary` and `#Preserved behavior` → actual route dispatch, request workspace, and retained Java/PDFBox operations → `Pdf4UmWebServer.java:141-166`; `Pdf4UmWebServerTest#bindsToLoopbackAndSupportsAllPdfWorkflows`.
- `t5-frontend.md#Preserved Workflows` and `t5-frontend-batch-report.yaml#evidence_mapping` → UI/API integration and download behavior → browser `app.js` request/error handlers; source comparison identified the JSON property mismatch in `app.js:427-434` versus `Pdf4UmWebServer.java:370-380`.

## Review Scope

Read-only review; no application source or configuration files were modified. The review does not replace the separately assigned full build/startup smoke test.
