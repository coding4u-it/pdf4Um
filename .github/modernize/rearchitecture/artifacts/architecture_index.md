# Architecture Index — Implementation Guide

## Boundary summary

Replace the current Swing entrypoint with a single Java process that serves a static browser workbench and its HTTP API. Retain the existing PDFBox transformations where practical. Bind the listener to IPv4 loopback `127.0.0.1` only. A browser file picker supplies bytes; the server must never receive or interpret a client filesystem path. Use temporary per-request storage and return outputs as downloads.

Keep `com.mycompany.pdf4um.Main` as the entrypoint class/FQCN so the existing VS Code Java launch configuration and Maven action continue to resolve. Do not overwrite `.vscode/launch.json`; it is an existing untracked user launch configuration.

**This index is not the full contract. Do not implement from this file alone; follow the artifact paths below.**

## Implementation Guide

### Global artifacts

- `unit_graph.yaml`
  - who reads: all implementation workers
  - use for: the single unit boundary, source anchors, and launch entrypoint
  - how to consume: implement `pdf-workbench`; anchors establish current behavior, not an automatic rewrite list.
- `migration_boundary.yaml`
  - who reads: all implementation workers
  - use for: exact implementation scope, preserved domain code, and files that may remain outside the runtime
  - how to consume: follow `must_rewrite`, `copy_as_is`, and `legacy_allowed_to_remain`; do not expand scope from source anchors.
- `wire_contracts.yaml`
  - who reads: backend and frontend workers
  - use for: concrete route, method, multipart fields, response media types, and error contracts
  - how to consume: implement each route as specified; keep browser requests same-origin and do not add CORS.
- `shared_modules.yaml`
  - who reads: implementation workers referencing shared code
  - use for: modules shared by more than one unit
  - how to consume: currently empty because the target boundary is one unit.
- `cross_unit_state.yaml`
  - who reads: implementation workers managing implicit state
  - use for: existing state flows between separate units
  - how to consume: currently no cross-unit flow was found; keep requests independent and avoid server-side user session state.
- `project-structure.md`
  - who reads: all implementation workers
  - use for: current package/layer layout and runtime entrypoint.
- `tech-stack.md`
  - who reads: backend/devops workers
  - use for: existing Java/Maven/PDFBox versions and compatibility constraints.
- `units/pdf-workbench/behavior.yaml`
  - who reads: backend and frontend workers
  - use for: operation rules, validation, output naming, and error paths.
- `units/pdf-workbench/bindings.yaml`
  - who reads: backend and frontend workers
  - use for: current Swing wiring being replaced, not copied into the browser target.
- `units/pdf-workbench/unit_decomposition.yaml`
  - who reads: design/implementation workers
  - use for: advisory-only split ideas; `commit: false` means no split decision is made here.
- No `seams.yaml`: no separate frozen legacy service or protocol cut was identified; the Java PDF logic remains in the same process.
- No `data-model.md`: no persistence or ORM/entity model was found.

### Unit: `pdf-workbench`

- external trigger: `GET /` browser page; `POST /api/split`, `/api/merge`, `/api/rename`, `/api/encrypt`, `/api/extract-text`.
- must read:
  - `units/pdf-workbench/behavior.yaml` — preserve the observed split, merge, rename, encryption, text, selection, and validation behavior.
  - `units/pdf-workbench/bindings.yaml` — replace Swing frame/menu/file chooser bindings with browser and HTTP bindings.
  - `units/pdf-workbench/unit_decomposition.yaml` — candidate splits only; do not treat them as required target structure.
- relevant global rows:
  - all `wire_contracts.yaml` rows where `unit: pdf-workbench`.
  - `shared_modules.yaml` is empty; no shared-module filtering is needed.
  - `cross_unit_state.yaml` has no flows; keep the new API request-scoped.
- before completion report: artifact paths read, preserved operation contracts, any deferred behavior, test/build evidence, and an HTTP probe demonstrating loopback startup. Confirm the server binds only to `127.0.0.1`, and report that `.vscode/launch.json` was preserved.

## Runtime and request rules

- The web listener is loopback-only; do not expose it to LAN/online clients.
- Serve the UI and API from the same origin; do not enable cross-origin access.
- Use multipart PDF uploads with bounded request size. Validate filenames and PDF content; write only under an isolated temporary workspace and clean it after the response.
- Return multiple generated files as a ZIP; return single merge output as PDF and extracted text as a text attachment.
- Avoid shared mutable controller/PDF-tool instances across concurrent requests; create per-request operation objects or serialize work.
- Route validation failures to `400`, unsupported media to `415`, invalid/unreadable PDF processing to `422`, and unexpected I/O failures to a generic `500` response. Keep filesystem paths and stack traces out of client responses.
