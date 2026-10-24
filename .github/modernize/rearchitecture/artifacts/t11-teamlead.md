# t11 — Runtime Evidence Conformance Review

## Verdict

**FAIL — user-approved functional and localhost acceptance criteria are supported by the evidence, but the runtime-validation conformance gate cannot pass.** Two HIGH findings remain: there is no approved testing-strategy artifact to compare against, and the browser-run report labels E2E `exit_code: 0` while explicitly stating that no process exit code was exposed. No production source or launch configuration was changed by this review.

## Acceptance Criteria Review

| User-approved criterion | Evidence | Result |
|---|---|---|
| Serve the browser app on this computer only | t7 source review and test assert a fixed `127.0.0.1` bind. t9 and t10 report runtime listeners on IPv4-mapped `127.0.0.1`; root and static resources returned HTTP 200. | **PASS** |
| Preserve split, ordered merge, rename, protect, and text extraction | t10 reports browser completion of all five flows. Its five JUnit tests validate output content/names, merge order, encrypted-PDF read-back with the submitted password, extracted text, static resources, and API contracts. | **PASS** |
| Preserve current work and avoid exposing paths/secrets or changing originals | Architecture review confirms uploads, request-scoped workspaces, same-origin requests, sanitized filenames, and attachment downloads. Browser evidence records retained selection and password clearing; existing `.vscode/launch.json` was reported preserved by t9/t10. | **PASS** |

The user-visible functional result is therefore supported. This is not, by itself, sufficient to sign off **testing-strategy conformance**.

## Conformance Findings

### HIGH — No approved Testing Strategy artifact

- `t10-tester.md` explicitly records that no approved Testing Strategy artifact was available. Searching the available rearchitecture materials finds no `Testing Strategy`, `primaryValidationStack`, critical-journey list, or fallback matrix.
- The existing UX and architecture artifacts define workflows and contracts, but do not establish the binding validation stack and evidence requirements needed for the runtime-validation conformance review.
- Consequently, this review cannot verify per-capability strategy adherence or decide whether missing Node.js/Playwright CLI, Docker, and browser-process evidence are accepted fallbacks. Missing design input cannot be inferred as approval.
- **Required remediation:** coordinator/planning owner must provide or explicitly approve the validation strategy and any fallback/deviation. Re-run this conformance check against that decision; request additional tester evidence only if the approved strategy requires it.

### HIGH — E2E exit-code evidence is internally inconsistent

- `t10-tester.md` records `e2e: PASS — exit_code: 0`, then qualifies that the integrated browser tool returned success but exposed **no OS process code**.
- Runtime-validation requires an observed exit code for each tier and requires `exit_code: 0` for a PASS verdict. The recorded `0` is not substantiated by the accompanying evidence, so E2E status is **UNVERIFIED for strict exit-code conformance**, although the report describes successful browser interactions for all five workflows.
- **Required remediation:** record an actual successful runner/process exit code, or report the E2E execution as tool-verified without asserting a process code and obtain explicit strategy-owner acceptance of that evidence form.

## Verification Evidence Reviewed

- t9: `mvn -B clean verify` returned 0; 2 passed, 0 failed/errors/skipped; packaged app served root and static assets; listener reported loopback.
- t10: `mvn -B clean test` returned 0; 5 passed, 0 failed/errors/skipped; `mvn -B package` returned 0; browser interactions reported 5/5 workflows.
- Independent verification in this task: `mvn -B clean verify` returned **0**; 5 passed, 0 failed, 0 errors, 0 skipped; `BUILD SUCCESS`. Maven emitted the existing missing `maven-jar-plugin` version and Java 11 system-modules-path warnings; PDFBox emitted fallback-font warnings.
- t8 recorded UX findings UX-1 through UX-3. t5.1 documents corresponding fixes and Chrome checks, including generic 400 feedback, retained focus, and error-state styling. This review did not independently replay those browser checks.

## Runtime Tier Summary

```text
environment:
  docker: UNAVAILABLE — t10 reports `docker info` could not connect to /var/run/docker.sock
  node: UNAVAILABLE — t10 reports node/npm/npx are not installed
  playwright: TOOL-AVAILABLE — integrated browser interactions reported success; local CLI/browser installation was unavailable
  infra-tier: NOT APPLICABLE — the application has no DB, broker, or external-service dependency; PDFBox runs in-process
  browser-tier: TOOL-EXECUTED — five browser workflows reported; strict process exit code unverified
startup: PASS — packaged JAR started; GET / returned 200; loopback listener reported at 127.0.0.1
integration: PASS — independent `mvn -B clean verify`, exit_code: 0, passed: 5, failed: 0, skipped: 0
e2e: UNVERIFIED — reported interactions: 5/5; reported exit_code 0 is not backed by an exposed process exit code
overall: FAIL — missing approved strategy and unsubstantiated E2E exit-code evidence prevent conformance sign-off
```

No auth-failure or database-persistence flow is applicable to this single-process app, which has no authentication or persistent database. Browser download-manager bytes were not directly verified; t10 reports response content verified in HTTP integration tests.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t2-ux.md` — approved five workflows and browser interaction requirements.
- `.github/modernize/rearchitecture/artifacts/t7-architect.md` — fixed loopback contract, server/API boundary, and test evidence.
- `.github/modernize/rearchitecture/artifacts/t8-ux.md` — workflow and accessibility review findings.
- `.github/modernize/rearchitecture/artifacts/t9-architect.md` — full-build, startup, listener, and static-resource evidence.
- `.github/modernize/rearchitecture/artifacts/t10-tester.md` — latest integration/browser execution results, environment capabilities, and its documented strategy gap.
- `.github/modernize/rearchitecture/artifacts/t1-architect.md` — architectural boundary and five preserved PDF operations.
- `.github/modernize/rearchitecture/artifacts/t5.1-frontend.md` — remediation claims and focused browser feedback/focus evidence.
- `.github/modernize/rearchitecture/board.md` — user-approved localhost-only scope and worktree preservation requirement.
- `.github/modernize/rearchitecture/context.md` and `decisions.md` were absent; no approved strategy was found among the available artifacts.

## Evidence Mapping

- `board.md#User Input` + `t2-ux.md#Operation workflows and controls` → acceptance matrix above; browser evidence mapped in `t10-tester.md#Browser execution details`.
- `t7-architect.md#Loopback-only binding` + `t9-architect.md#Startup and HTTP Evidence` → loopback acceptance row and startup tier; independent verification supports full build/test status.
- `t10-tester.md#Runtime Validation Verdict` + `t10-tester.md#Upstream Artifacts Consumed` → missing-strategy HIGH finding and the explicit E2E exit-code contradiction.
- `t8-ux.md#Findings` + `t5.1-frontend.md#Test Results` → review-finding remediation evidence; no new browser replay claimed.

## Test Results

- Command: `mvn -B clean verify`
- Passed: 5
- Failed: 0
- Errors: 0
- Skipped: 0
- Exit code: 0
- Additional run: none. The tester's reported browser execution was reviewed, not repeated in this conformance task.

## Findings

- HIGH: 2
- CRITICAL: 0
- MEDIUM/LOW: 0
- **Gate result: FAIL** (binary verdict; HIGH findings prevent PASS).
