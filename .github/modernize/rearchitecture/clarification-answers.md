---
schema: clarification-answers/v1
status: submitted
generated_at: "2026-10-22T16:46:21.264Z"
scope: [frontend, backend, generic]
questions_file: clarification-questions.json
---

# Rearchitecture Clarification Answers

## 🖥️ Frontend

- **F1** Which UI framework and version should the MVC refactor target? If this is only a structural refactor, should it retain the project's existing Java UI framework and version?
  - answer: Java Swing (specify Java version)
  - source: user
- **F2** Should the MVC refactor keep the current UI components, or use a specific Java UI component library?
  - answer: Swing standard components
  - source: user
- **F3** If the desktop UI is in scope, provide paths to screenshots or a recording of its current behavior and appearance. If no UI changes are intended, say so.
  - answer: _none_
  - source: skipped (required, no default — blocking gap)
- **F4** What visual guidance should the refactor follow? For example, preserve the existing appearance and assets, or provide a design system/reference.
  - answer: match existing pixel-by-pixel using extracted CSS custom properties
  - source: user
- **F5** Which accessibility standard should the UI meet, if applicable?
  - answer: WCAG 2.1 AA
  - source: user
- **F6** What runtime or platform compatibility targets should be preserved for the UI?
  - answer: preserve current runtime compatibility
  - source: default applied
- **F7** Should the refactor preserve the current desktop layout, or is responsive/adaptive behavior also required?
  - answer: preserve current layout and behavior
  - source: user
- **F8** Which languages/locales should remain supported?
  - answer: preserve current locales; keep existing i18n library if present
  - source: default applied
- **F9** Do you have a preference for how UI state should be managed?
  - answer: preserve existing pattern if identifiable; otherwise use a minimal approach
  - source: default applied
- **F10** Should the refactor preserve the existing navigation strategy, or use another approach?
  - answer: preserve existing navigation strategy
  - source: default applied

## ⚙️ Backend

- **B1** Which backend/application framework and version should the refactor target? If this is only an MVC separation, should it retain the existing Java framework and version?
  - answer: Keep the existing Java framework and version (identify from the project)
  - source: user
- **B2** If the application exposes APIs or service contracts, what compatibility policy should the refactor follow?
  - answer: must preserve
  - source: user
- **B3** If the application has persistent data, should the refactor change its schema or storage, or leave data migration out of scope?
  - answer: no migration
  - source: user
- **B4** If authentication or authorization exists, should the refactor preserve the current mechanism?
  - answer: preserve existing auth mechanism; detect from codebase
  - source: default applied
- **B5** Are there performance or availability targets the refactor must maintain?
  - answer: match current production baseline; no regression
  - source: default applied

## 📋 General

- **G1** What should count as a successful MVC refactor?
  - answer: Preserve existing behavior while refactoring the project into an appropriate MVC architecture
  - source: user
- **G2** Are there files, components, or behaviors that must not be changed?
  - answer: no explicit exclusions; infer from project structure
  - source: default applied
- **G3** How should existing tests be treated during the refactor?
  - answer: must pass
  - source: user
- **G4** Where should the refactored code be placed?
  - answer: in-place
  - source: user
- **G5** Any additional requirements, exclusions, dependencies, compliance rules, or operational constraints?
  - answer: None beyond the decisions listed in this specification.
  - source: user
