# t5 — Local PDF Workbench Browser UI

## Summary

Implemented a responsive, Italian-language browser workbench for the existing localhost PDF service. It covers all five PDF operations, sends selected file bytes to the same-origin API, and exposes generated results as downloads. The interface does not display client filesystem paths and clearly states that it is available only on this computer.

## Deliverables

- [t5-frontend-batch-report.yaml](./t5-frontend-batch-report.yaml) — structured implementation, upstream traceability, and test results.
- `src/main/resources/web/index.html` — accessible workbench structure, operation settings, permission controls, and result/status region.
- `src/main/resources/web/app.js` — file selection and ordering, field validation, same-origin API requests, localized errors, and downloads.
- `src/main/resources/web/styles.css` — responsive workbench styling, visible focus, and narrow-screen reflow.

## Preserved Workflows

- **Dividi:** one-page-per-file default or positive pages-per-part groups; ZIP result.
- **Unisci:** at least two selected PDFs, keyboard-operable ordering, and first-file output naming communicated before submission.
- **Rinomina:** sequential prefix/number or random code length/symbol options; ZIP result and `esporta.csv` explanation.
- **Proteggi:** blank required password, five allow-permission controls, and ZIP result; password clears after success.
- **Estrai testo:** one selected PDF and UTF-8 text download.
- **Shared behavior:** add/remove/clear selection, duplicate suppression, selected names without paths, 32-file cap, progress/result/error feedback, retry link, and preservation of the selected list after failure.

## Exact Project Files Changed by t5

- `src/main/resources/web/index.html` — created.
- `src/main/resources/web/app.js` — created.
- `src/main/resources/web/styles.css` — created.

The frontend task did not modify Java source, `README.md`, or `.vscode/launch.json`. Existing user and backend worktree changes were left intact. No commit was created.

## Test Results

- Command: `mvn -B clean test package`
- Passed: 2
- Failed: 0
- Skipped: 0
- Failures: none.
- Existing HTTP integration tests passed for split, merge, rename, encrypt, and text extraction.
- Packaged-JAR probes: `GET /`, `/app.js`, and `/styles.css` each returned HTTP 200.
- Headless Chrome interaction checks passed for operation switching, split-group field validation, merge minimum/count/order, random rename controls, encryption password/permissions, extract-text action, clear-selection behavior, the 32-file cap, and a 375px mobile viewport without horizontal overflow.
- `git diff --check` passed.
- Maven emitted existing configuration warnings for an unpinned `maven-jar-plugin` version and Java 11 source/target compilation without an explicit system-modules path; neither blocked the build.

## Limitations and Blockers

- Each workflow supports at most 32 PDFs; the server request limit is 100 MiB. The UI enforces the file-count cap and displays the byte limit, while an oversized request receives a localized error from the server response.
- Browser file contents are uploaded to the local process and outputs are downloaded; the interface intentionally cannot access arbitrary client paths or overwrite selected originals.
- No blocking issue remains for the frontend task.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/board.md` — user-selected localhost-only scope and preservation requirements.
- `.github/modernize/rearchitecture/artifacts/t1-architect.md` — operation inventory, local server boundary, and architecture navigation.
- `.github/modernize/rearchitecture/artifacts/t2-ux.md` — Italian workbench structure, workflows, interaction and accessibility requirements.
- `.github/modernize/rearchitecture/artifacts/t3-devops.md` — active Java/Maven/Chrome environment.
- `.github/modernize/rearchitecture/artifacts/t4-backend-implementation.md` — static resource allowlist, endpoint fields, response handling, and upload/workspace behavior.
- `.github/modernize/rearchitecture/artifacts/t4-backend-batch-report.yaml` — HTTP integration-test evidence for the five operation endpoints.
- `.github/modernize/rearchitecture/artifacts/wire_contracts.yaml` — request fields, status and download contracts.
- `.github/modernize/rearchitecture/artifacts/migration_boundary.yaml` — runtime-reachable frontend paths and safe browser-upload boundary.
- `.github/modernize/rearchitecture/artifacts/units/pdf-workbench/behavior.yaml` — legacy workflow branches, validation, and output behavior.
- `.github/modernize/rearchitecture/learnings/architect/localhost-pdf-web-boundary.md` — same-origin loopback boundary, temporary uploads, and no client path assumptions.

## Evidence Mapping

- `t2-ux.md#Primary page and navigation` and `#Selected-file behavior` → `index.html` / `app.js` → Chrome confirmed file list, clear action, merge reordering, and accessible operation switching.
- `t2-ux.md#Operation workflows and controls` → `app.js` and operation settings in `index.html` → Chrome checks passed for all five controls and validation paths.
- `wire_contracts.yaml#POST /api/split, /api/merge, /api/rename, /api/encrypt, /api/extract-text` → `app.js` multipart field construction and download handling → the existing Java HTTP integration tests passed for all five routes.
- `wire_contracts.yaml#GET /` and backend static allowlist → the three bundled resources → packaged-JAR probes returned HTTP 200 for `/`, `/app.js`, and `/styles.css`.
- `board.md#User Input` → the local-only notice and same-origin requests → app served from `127.0.0.1` during packaged browser verification; no launch configuration was edited.
