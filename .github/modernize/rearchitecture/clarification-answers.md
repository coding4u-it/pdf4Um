---
schema: clarification-answers/v1
status: submitted
generated_at: "2026-10-24T17:08:47.937Z"
scope: [frontend, backend, generic]
questions_file: clarification-questions.json
---

# Rearchitecture Clarification Answers

## 🖥️ Frontend

- **F1** Which browser UI framework or implementation style should the new interface use?
  - answer: Plain HTML/CSS/JavaScript (no frontend framework)
  - source: user
- **F2** Should the browser UI use a component library, or keep to lightweight native browser controls?
  - answer: No component library; native HTML controls and minimal CSS
  - source: user
- **F3** Do you have screenshots or recordings of the Swing UI to guide visual reproduction? If not, confirm that functionality matters more than pixel-perfect appearance.
  - answer: _none_
  - source: skipped (required, no default — blocking gap)
- **F4** What visual design system or token source should guide the browser UI? For example, use simple native controls without pixel matching, or provide a brand/design reference.
  - answer: No custom design system; prioritize functional parity with a simple accessible native-browser UI
  - source: user
- **F5** Which accessibility standard should be targeted?
  - answer: WCAG 2.1 AA
  - source: user
- **F6** Which browser targets should be supported?
  - answer: modern evergreen (Chrome, Firefox, Safari, Edge — latest 2 major versions)
  - source: user
- **F7** What responsive layout strategy should the web UI use?
  - answer: mobile-first using existing breakpoints detected from codebase
  - source: user
- **F8** Which interface languages are in scope?
  - answer: preserve current locales; keep existing i18n library if present
  - source: user
- **F9** What client-side state approach do you prefer?
  - answer: preserve existing pattern if identifiable; otherwise recommend minimal (component state + server-state library)
  - source: user
- **F10** What browser routing strategy should be used?
  - answer: use the de-facto router for the chosen target framework
  - source: user

## ⚙️ Backend

- **B1** What Java server framework or approach should expose the PDF functionality to the browser?
  - answer: Spring Boot (choose a compatible version)
  - source: user
- **B2** How should the new web boundary handle existing external APIs or contracts?
  - answer: must preserve
  - source: user
- **B3** What database/data migration approach should be used?
  - answer: TBD / assess in research phase
  - source: user
- **B4** What authentication policy should apply to the localhost-only application?
  - answer: preserve existing auth mechanism; detect from codebase
  - source: user
- **B5** What performance target should the local application meet?
  - answer: match current production baseline; no regression
  - source: user

## 📋 General

- **G1** What observable outcomes define success?
  - answer: Preserve existing user-visible PDF functionality in a browser UI served only on localhost; keep Java/PDFBox logic where practical; document consistent launch/run instructions; run focused build/tests; report changes and limitations; do not commit.
  - source: user
- **G2** Are any areas explicitly out of scope?
  - answer: Do not revert or alter unrelated worktree changes, especially .vscode/launch.json; do not expose the service on the LAN or online; do not commit.
  - source: user
- **G3** What is the required policy for existing tests?
  - answer: must pass
  - source: user
- **G4** Should this conversion update the existing project in place or use a new directory?
  - answer: in-place
  - source: user
- **G5** Are there any additional constraints, requirements, exclusions, dependencies, or operational rules?
  - answer: Localhost-only (not LAN/online); preserve the recent .vscode/launch.json and all unrelated worktree changes; do not commit.
  - source: user
