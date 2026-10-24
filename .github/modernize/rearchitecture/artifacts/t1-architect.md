# t1 — Existing PDF workflows and localhost web boundary

## Summary

The existing project is a small, single-module Java Swing application. Keep its Java/PDFBox transformation logic and preserve `com.mycompany.pdf4um.Main` as the launch class, but replace its Swing runtime with one loopback-bound HTTP process, a browser workbench, and operation endpoints. Browser uploads are processed in temporary storage and returned as downloads; user originals are not changed.

## Deliverables

- [architecture_index.md](./architecture_index.md) — implementation navigation guide and proposed web/API boundary.
- [migration_boundary.yaml](./migration_boundary.yaml) — smallest runtime rewrite scope and safe file-workspace contract.
- [unit_graph.yaml](./unit_graph.yaml) — one externally triggered workbench unit and its existing source anchors.
- [units/pdf-workbench/behavior.yaml](./units/pdf-workbench/behavior.yaml) — existing operation semantics and user-visible branches.
- [units/pdf-workbench/bindings.yaml](./units/pdf-workbench/bindings.yaml) — current Swing bindings to replace.
- [units/pdf-workbench/unit_decomposition.yaml](./units/pdf-workbench/unit_decomposition.yaml) — advisory split candidates (no target split committed).
- [wire_contracts.yaml](./wire_contracts.yaml) — concrete proposed HTTP contracts.
- [shared_modules.yaml](./shared_modules.yaml) — no cross-unit shared-module rows in the single-unit boundary.
- [cross_unit_state.yaml](./cross_unit_state.yaml) — no existing cross-unit implicit state identified.
- [project-structure.md](./project-structure.md) — current project layers, entrypoint, and package structure.
- [tech-stack.md](./tech-stack.md) — current versions, dependencies, and runtime facts.

## Key decisions

- Bind explicitly to `127.0.0.1`; do not bind to `0.0.0.0` or a LAN interface.
- Keep the existing main-class FQCN so the current `.vscode/launch.json` and `nbactions.xml` launch references remain usable; do not overwrite the user's untracked launch file.
- Expose the five existing workflows through same-origin HTTP routes: split, merge, rename, encrypt, and extract text.
- Treat the browser-selected files as uploads, not server paths. Process in a per-request temporary workspace and return generated files as attachments/ZIP downloads.
- Avoid sharing mutable `Pdf4UmController` / `PdfTools` instances across concurrent requests. Use request-scoped instances or serialize PDF operations.
- The current rename implementation writes `esporta.csv` in the process working directory and performs in-place renames. Adapt those effects to the temporary workspace and downloadable outputs so the web app neither changes user originals nor writes outside its workspace.

## Existing behavior evidence

- Multi-file selection and selected-name display: `Main.java:399`, `Main.java:629-635`.
- Menu operations and validation/error dialogs: `Main.java:717-795`; controller validation: `Pdf4UmController.java:28-79`.
- PDF split, merge, encryption, and text extraction: `PdfTools.java:103-198`.
- Rename modes and CSV side effect: `Pdf4UmModel.java:19-34`; filename operations: `FileOperazioni.java:24-49`.
- Java 11 compiler source/target and PDFBox 2.0.26: `pom.xml`.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/board.md` — task requirement, explicit localhost-only choice, and preservation of the existing launch configuration.
- `.github/modernize/rearchitecture/artifacts/project-profile.yaml` — single-module Java project, approximate LOC, source-root, and rewrite classification.
- No task dependency artifacts were provided.

## Evidence Mapping

- `board.md#User Input` → loopback-only bind, retained Java/PDFBox boundary, launch-class continuity, and safe treatment of `.vscode/launch.json`.
- `project-profile.yaml#project` → current project structure and scope in `project-structure.md` / `tech-stack.md`.
- `Main.java` / controller / PDF model source anchors → operation behaviors in `units/pdf-workbench/behavior.yaml` and proposed route contracts in `wire_contracts.yaml`.

## Test Results

- Command: source and worktree inspection only; no source changes or build/test command were part of this architecture task.
- Passed: not applicable.
- Failed: 0.
- Skipped: build/runtime verification belongs to the assigned smoke-test task; no existing `src/test` files were found.
