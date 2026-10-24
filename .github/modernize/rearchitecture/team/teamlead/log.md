## [t11] Reviewed runtime evidence against localhost PDF acceptance
- Codebase/domain discoveries: the t10 runtime report supports all five browser workflows and loopback-only startup; independent `mvn -B clean verify` now covers five tests, while t9's earlier full build covered two.
- Wrong assumptions and corrections: successful integrated browser interactions are not equivalent to a process exit code when the report explicitly says no OS code was exposed; recorded `exit_code: 0` cannot be treated as independently evidenced.
- Debugging dead-ends and what actually worked: searching all available rearchitecture materials confirmed the missing approved Testing Strategy artifact; the UX/architecture contracts establish user workflows but not a binding test stack/fallback matrix.
- Techniques/patterns worth reusing for future tasks: separate user-acceptance evidence (feature journey + loopback) from process conformance; report per-tier evidence and use a binary gate verdict where required.
- Learnings consumed: []

## [t11.1] Defined localhost PDF workflow test strategy
- Codebase/domain discoveries: the workbench has five browser workflows, a JDK HTTP server, PDFBox in-process, and no database or external service; existing target-side JUnit tests use ephemeral loopback ports and generated PDFs.
- Wrong assumptions and corrections: Docker unavailability is irrelevant without external infrastructure; missing local Node/npm does not establish that the integrated browser tool is unavailable. A browser-tool result must not be presented as an OS process exit code.
- Debugging dead-ends and what actually worked: the canonical Maven baseline ran successfully with five tests; cross-checking UX and backend artifacts made each required flow and response assertion concrete.
- Techniques/patterns worth reusing for future tasks: separate capability axes; use real returned bytes for PDF assertions; record native tool status when no process return code exists.
- Learnings consumed: [tester/junit-http-workflow-fixtures]
