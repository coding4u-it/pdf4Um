# t4 — Localhost PDF backend implementation

## Summary

Implemented the Java HTTP server and five PDF workflow endpoints on the retained `com.mycompany.pdf4um.Main` entrypoint. It binds only to `127.0.0.1`, processes bounded browser uploads in isolated temporary workspaces, and reuses the existing PDFBox transformations.

## Deliverables

- [t4-backend-implementation.md](./t4-backend-implementation.md) — route behavior, preserved functionality, worktree/file scope, runtime probe, and limitations.
- [t4-backend-batch-report.yaml](./t4-backend-batch-report.yaml) — structured implementation, traceability, and test report.
- [checkpoints/tasks-to-impl.yaml](./checkpoints/tasks-to-impl.yaml) — t4 implementation checkpoint.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t1-architect.md` — implementation index and design decisions.
- `.github/modernize/rearchitecture/artifacts/wire_contracts.yaml` — route methods, multipart fields, media types, and HTTP error contracts.
- `.github/modernize/rearchitecture/artifacts/migration_boundary.yaml` — loopback-only runtime scope, retained entrypoint, temporary-workspace rule, and preservation of `.vscode/launch.json`.
- `.github/modernize/rearchitecture/artifacts/units/pdf-workbench/behavior.yaml` — PDF workflow branches, file naming, and existing validation/error behavior.
- `.github/modernize/rearchitecture/artifacts/units/pdf-workbench/bindings.yaml` — replacement of Swing entrypoint and file-picker bindings.
- `.github/modernize/rearchitecture/artifacts/project-structure.md` — current Java layers and launch references.
- `.github/modernize/rearchitecture/artifacts/t3-devops.md` — active Java/Maven environment and runtime expectations.
- `.github/modernize/rearchitecture/learnings/architect/localhost-pdf-web-boundary.md` — loopback, upload isolation, and request-scoped operation guidance.
- `.github/modernize/rearchitecture/board.md` — explicit localhost-only user requirement and preservation constraints.

## Evidence Mapping

- `wire_contracts.yaml#GET / and POST /api/*` → `Pdf4UmWebServer` route handlers; `Pdf4UmWebServerTest#bindsToLoopbackAndSupportsAllPdfWorkflows`; successful 200 responses for all five POST routes.
- `migration_boundary.yaml#must_rewrite and copy_as_is` → retained `Main` FQCN, stateless request-supplied controller, PDFBox model operations, and explicit-path file helpers; `mvn -B clean test package`.
- `behavior.yaml#side_effects, branches, and error_paths` → split, merge, sequential/random rename, encryption, and text extraction transformations; positive and negative endpoint integration tests.
- `board.md#User Input` and `t3-devops.md#Target Environment Preparation` → README launch command and loopback-only bind; packaged-JAR launch probe confirmed the listener address as `127.0.0.1`.

## Test Results

- Command: `mvn -B clean test package`
- Passed: 2 tests
- Failed: 0
- Skipped: 0
- Coverage: successful split, merge, sequential/random rename, encryption, and text extraction requests; loopback address; 400/415/422/404 error paths.
- Package: `target/Pdf4Um-1.0-SNAPSHOT-jar-with-dependencies.jar` produced successfully.

## Current Integration Note

The packaged-JAR launch probe confirmed the process starts and listens on loopback. At the time of this backend task, the frontend-owned `src/main/resources/web/` assets did not yet exist, so `GET /` correctly returned 503 with a clear “browser workbench has not been packaged” response. Once the frontend task adds `index.html`, `app.js`, and `styles.css` to that resource path, the same server serves them at `/`, `/app.js`, and `/styles.css`.
