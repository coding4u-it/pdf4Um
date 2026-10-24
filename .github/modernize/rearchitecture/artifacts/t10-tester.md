# t10 — Focused Regression and Browser Workflow Validation

**Generated:** 2026-10-24T17:40:49Z  
**Target:** `/home/france/gitHub/pdf4Um`

## Summary

The localhost PDF workbench started from the packaged JAR and responded on the loopback address. Five Maven tests passed, including three new workflow regression tests, and the integrated browser completed all five user-facing operations: split, merge, rename, protect, and text extraction. No application source, launch configuration, or existing unrelated worktree changes were modified by t10.

| Validation step | Status | Exit/result | Evidence |
|---|---|---|---|
| Startup and static UI | PASS | root, `/app.js`, `/styles.css`: HTTP 200 | Packaged JAR on port 28764; listener reported IPv4-mapped `127.0.0.1` |
| Maven regression | PASS | `mvn -B clean test`: 5 passed, 0 failed/errors/skipped | Surefire XML reports |
| Package verification | PASS | `mvn -B package`: exit 0; 5 tests passed | Executable dependency JAR produced |
| Browser workflows | PASS | 5 of 5 operations completed | Integrated Playwright browser interactions against the running app |
| Whitespace | PASS | `git diff --check`: exit 0 | No whitespace errors |

## Runtime Validation Verdict

```text
environment:
  docker: UNAVAILABLE — `docker info` failed: cannot connect to unix:///var/run/docker.sock (no such file or directory)
  node: UNAVAILABLE — `node` and `npx` binaries are not installed
  playwright: AVAILABLE — integrated browser Playwright interactions passed; the separate appmod debug launcher could not find its cached Chromium executable
  infra-tier: FALLBACK(embedded/in-memory) — no database, broker, or external service is part of the implemented app; tests use the real local Java HTTP server and PDFBox. Docker daemon unavailable.
  browser-tier: PRIMARY(Playwright) — integrated browser ran the app in a real browser page and exercised all five operations
startup: PASS — `java -Dpdf4um.port=28764 -jar target/Pdf4Um-1.0-SNAPSHOT-jar-with-dependencies.jar`; first readiness probe returned `GET /` HTTP 200 in under 1 second; listener was `127.0.0.1`
integration: PASS — exit_code: 0, passed: 5, failed: 0, skipped: 0; split/merge, rename/protect, extracted text/UI assets, loopback, and negative API contracts
e2e: PASS — exit_code: 0 (integrated browser tool returned success; no OS process code is exposed), passed: 5, failed: 0; split, ordered merge, sequential rename, password-protected copy, and text extraction; upload, validation, result status, download link/name, selection retention, and password clearing exercised
overall: NEEDS_SIGNOFF — all implemented journeys passed; the dependency set contains no approved Testing Strategy artifact, so the coordinator must accept the documented strategy deviation
```

### Browser execution details

- **Split:** uploaded one PDF and submitted the default one-page split; completion appeared and the result link was `split-pdfs.zip`.
- **Merge:** uploaded two PDFs in visible order and submitted; both names remained visible in that order and the result link was `pdf4um-first_merged.pdf`.
- **Rename:** set sequential prefix `E2E-`; completion appeared, `renamed-pdfs.zip` was offered, and the selected file remained in the workbench.
- **Protect:** verified the action was disabled with a blank password; supplied a test-only password, completed the request, received `encrypted-pdfs.zip`, and verified the password field was cleared.
- **Extract text:** uploaded one PDF and submitted; completion appeared, the link was `pdf4um-browser-validation_text.txt`, and the selected file remained visible.
- The integrated browser page was opened at `http://127.0.0.1:28764/`. Application resource GETs for the page, JavaScript, and stylesheet returned 200.
- A separate `appmod-debug-app-in-browser` attempt failed before launching because its expected cached executable (`chromium_headless_shell-1200/.../chrome-headless-shell`) was absent. The integrated browser Playwright API was available and successfully exercised the workflows, so no browser-tier fallback was used.

## Test Results

- Command: `mvn -B clean test`
- Passed: 5
- Failed: 0
- Errors: 0
- Skipped: 0
- Failure details: none.
- Additional command: `mvn -B package` — exit 0; the same 5 tests passed and the dependency JAR was built.
- Test classes: `Pdf4UmWebServerTest` (2 tests), `SplitMergeWorkflowTest` (1), `RenameProtectWorkflowTest` (1), and `TextExtractionWorkbenchWorkflowTest` (1).
- Existing Maven warnings remain: `maven-jar-plugin` has no pinned version and Java 11 source/target compilation has no explicit system-modules path. PDFBox also logged fallback-font warnings. None affected the result.

## Coverage and Limitations

- Regression tests read generated PDF/ZIP contents back with PDFBox, verify merge order and output names, open the encrypted output with the submitted test password, check extracted UTF-8 text, and assert that the HTML and static assets are served.
- Existing integration coverage also exercises random rename/CSV behavior, invalid merge count (400), unsupported file type (415), unreadable PDF (422), unknown route (404), and exact loopback binding.
- The app has no authentication or persistent data store by design; authentication-failure and database-persistence checks are not applicable. Uploaded documents are request-scoped temporary data; integration tests validate generated result bytes but do not inspect user disk files. Browser tests checked download link metadata/status, not the browser's download-manager file bytes; response bytes are covered by integration tests.
- The local Node/npm/npx toolchain and local Playwright Chromium cache are unavailable. Integrated browser automation remained available and was used successfully.
- Docker is installed as a CLI but its daemon is unavailable. No Docker-managed service is required by this single-process PDFBox app.

## Task Files Added

- `src/test/java/com/mycompany/pdf4um/web/WebWorkflowTestSupport.java` — shared ephemeral-server, multipart, PDF fixture, and ZIP helpers.
- `src/test/java/com/mycompany/pdf4um/web/SplitMergeWorkflowTest.java` — split output and ordered merge regression flow.
- `src/test/java/com/mycompany/pdf4um/web/RenameProtectWorkflowTest.java` — renamed-copy and encrypted-output regression flow.
- `src/test/java/com/mycompany/pdf4um/web/TextExtractionWorkbenchWorkflowTest.java` — static workbench and extracted-text workflow regression flow.
- `.github/modernize/rearchitecture/artifacts/t10-tester.md` — this report.
- `.github/modernize/rearchitecture/team/tester/log.md` — tester session notes.
- `.github/modernize/rearchitecture/learnings/tester/junit-http-workflow-fixtures.md` — reusable test-fixture learning.

No production source, README, `.vscode/launch.json`, or unrelated worktree files were changed by t10. The running application was stopped after testing; a final request to port 28764 failed to connect, confirming shutdown.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t2-ux.md` — five user-visible flows and UI interaction requirements used to select browser journeys.
- `.github/modernize/rearchitecture/artifacts/t4-backend.md` and `t4-backend-implementation.md` — route behavior, response formats, error status contracts, and test scope.
- `.github/modernize/rearchitecture/artifacts/t5-frontend.md` — expected browser UI and downloadable operation results.
- `.github/modernize/rearchitecture/artifacts/t5.1-frontend.md` — final error feedback, focus, and result-state changes to retain.
- `.github/modernize/rearchitecture/artifacts/t7-architect.md` — fixed loopback contract and prior error-shape finding/remediation target.
- `.github/modernize/rearchitecture/artifacts/t8-ux.md` — workflow/accessibility review findings and validation context.
- `.github/modernize/rearchitecture/artifacts/t9-architect.md` — packaged-JAR launch command, expected static paths, and full-build baseline.
- `.github/modernize/rearchitecture/artifacts/t1-architect.md` and `wire_contracts.yaml` — runtime boundary, PDF operation contracts, and expected HTTP responses.
- `.github/modernize/rearchitecture/artifacts/t3-devops.md` — Java, Maven, Chrome, Node, and Docker environment expectations.
- `.github/modernize/rearchitecture/board.md` — localhost-only scope and preservation constraint.
- No approved Testing Strategy artifact was present in the dependency set or available artifact directory. `.github/modernize/rearchitecture/context.md`, `decisions.md`, and the tester `log.md`/`inbox.md` did not exist before t10.

## Evidence Mapping

- `t2-ux.md#Operation workflows and controls` → integrated browser actions → successful split, ordered merge, sequential rename, password protection, and text extraction results.
- `t4-backend.md#Test Results` and `wire_contracts.yaml#Split PDF,Merge PDFs,Rename PDFs,Encrypt PDFs,Extract text` → JUnit HTTP workflow tests → PDF/ZIP response content, expected names, encrypted read-back, extracted text, and negative status contracts.
- `t7-architect.md#Loopback-only binding` and `t9-architect.md#Startup and HTTP Evidence` → JUnit loopback assertion plus current packaged-JAR listener/HTTP probes → `127.0.0.1` bind and 200 responses for root/static assets.
- `t5-frontend.md#Preserved Workflows` and `t5.1-frontend.md#Summary` → actual browser workflows → success/status/download links, retained selection, and password clearing verified.
- `t3-devops.md#Target Environment Preparation` → current tool availability probes → exact unavailable Docker daemon and Node/npm/npx status; integrated browser Playwright was used despite missing local CLI tooling.
