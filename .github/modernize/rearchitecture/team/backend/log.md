## [t4] Implementing the localhost-only PDF backend

- Codebase/domain discoveries: Existing PDFBox methods write beside their inputs; the browser boundary can preserve their naming/transformations by placing uploads in a private request workspace and only returning generated paths. Random rename previously wrote `esporta.csv` to process CWD, so the web path now creates renamed copies and puts the CSV in its output ZIP.
- Wrong assumptions and corrections: No frontend resource directory existed when packaging/launching this backend task. `GET /` therefore returned the deliberate 503 “workbench has not been packaged” response; the frontend task must add the three allowlisted resources for the page to return 200. This is not a REST-operation failure.
- Debugging dead-ends and what actually worked: Initial compile checks caught a missing `File` import and, after removing old controller state, one stale extraction method name. Correcting both and running a clean Maven test/package verified the complete server/test source.
- Techniques/patterns worth reusing: Use the JDK `HttpServer` to avoid adding a production web framework for this single-process local app; parse bounded multipart bytes, validate PDFs before transforming, create controller/model instances per request, stream attachment/ZIP outputs, and delete the request directory in `finally`.
- Learnings consumed: [architect/localhost-pdf-web-boundary]

## [t6] Scanning Maven dependencies for CVEs
- Codebase/domain discoveries: `mvn dependency:list -DincludeScope=test` resolved five coordinates: PDFBox 2.0.26, FontBox 2.0.26, Commons Logging 1.2, JUnit 4.13.2, and Hamcrest Core 1.3.
- Wrong assumptions and corrections: The frontend task added only static browser assets; the only changed dependency manifest was the Maven POM, where JUnit is test-scoped.
- Debugging dead-ends and what actually worked: Quiet dependency listing omitted resolved coordinates; rerunning without `-q` produced the complete compile-and-test dependency set.
- Techniques/patterns worth reusing: Run the shared Maven CVE assessment against resolved direct and transitive coordinates, retain initial and final scan JSON, and verify the complete Maven lifecycle even when no upgrade is needed.
- Learnings consumed: [backend/localhost-pdf-api-boundary]
