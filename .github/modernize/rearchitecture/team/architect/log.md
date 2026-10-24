## [t1] Defined localhost PDF workbench boundary
- Codebase/domain discoveries: this is one Java 11-targeted Maven module with a Swing entrypoint, a controller that stores selected files/password as instance state, and PDFBox/file helper classes. Existing workflows include split, merge, sequential/random rename, encryption, and text extraction. The rename path writes `esporta.csv` to process CWD and renames source files in place.
- Wrong assumptions and corrections: project is not currently a web backend; browser uploads cannot preserve filesystem-path semantics. Preserve user functionality by returning generated copies/downloads rather than modifying client originals.
- Debugging dead-ends and what actually worked: generated `Main.java` layout code was large; targeted inspection of action handler ranges and controller/model methods made operation behavior clear.
- Techniques/patterns worth reusing: maintain the existing `Main` FQCN to keep the user-owned `.vscode/launch.json` and Maven action viable; ensure temporary file workspaces and request-scoped PDF state prevent accidental CWD writes and request races.
- Learnings consumed: []

## [t7] Reviewed localhost web boundary and loopback binding
- Codebase/domain discoveries: the listener is constructed on the literal IPv4 address `127.0.0.1`, and the HTTP integration test asserts this exact address while exercising all five PDF routes.
- Wrong assumptions and corrections: earlier task reports claimed localized server error parsing; comparing both ends showed the backend returns JSON `error` while the UI reads `message`, so server-provided validation details are discarded.
- Debugging dead-ends and what actually worked: no runtime debug was needed; source line comparison plus `mvn -B test` verified the binding and endpoint behavior.
- Techniques/patterns worth reusing: check both sides of JSON contracts, not just route and multipart field names; carry the property name through the server serializer and browser parser.
- Learnings consumed: [architect/localhost-pdf-web-boundary, backend/localhost-pdf-api-boundary, frontend/local-pdf-workbench-ui]

## [t9] Independently verified packaged localhost startup
- Codebase/domain discoveries: the shaded Maven JAR serves the final browser root and static assets; its measured root-readiness time was 178 ms when started on an alternate local port.
- Wrong assumptions and corrections: prior backend smoke evidence predated the browser assets and returned 503; after frontend delivery the same root endpoint responds 200.
- Debugging dead-ends and what actually worked: `mvn -B clean verify` rebuilt the complete project and ran both HTTP integration tests; `ss` confirmed `[::ffff:127.0.0.1]` and `curl` confirmed the remote peer was `127.0.0.1`.
- Techniques/patterns worth reusing: measure readiness from process launch to a successful HTTP request and stop the packaged process after the probe.
- Learnings consumed: [architect/localhost-pdf-web-boundary]
