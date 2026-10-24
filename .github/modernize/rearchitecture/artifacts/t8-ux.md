# t8 — Browser workflow UX review

## Summary

The delivered workbench preserves the five specified PDF workflows and provides a clear Italian, localhost-only upload/process/download journey. Selection order, operation-specific controls, naming/output expectations, validation feedback, and responsive layout are represented. Source review found one generic server-validation error-path defect and two keyboard/feedback polish gaps; details follow.

## Workflow Preservation Review

| Workflow / shared behavior | Review |
|---|---|
| Select multiple PDFs, view names without paths, append additional selection, remove/clear, and retain originals | Present. File count and aggregate request limit are stated; selection remains visible during processing. |
| Split one file, one-page default or positive pages-per-part, numbered ZIP outputs | Present. Controls and helper text match the documented endpoint behavior. |
| Merge at least two files in visible order, first filename as output base | Present. Up/down buttons are keyboard-operable and the naming consequence is stated. |
| Sequential/random rename settings and `esporta.csv` mapping | Present. Mode-specific settings are shown conditionally; result and original-copy behavior are explained. |
| Protect copies with password and five permission controls | Present. Password starts blank, uses password input semantics, clears after success, and permission labels explain allowed vs restricted choices. |
| Extract text from one file as UTF-8 `.txt` | Present. The action and output format are identified. |
| Progress, success/download, retry link, and operation errors | Present, with an implementation defect for generic HTTP 400 responses (finding UX-1). |
| Keyboard access and responsive reflow | Mostly present: native controls, visible focus styling, accessible names, live status/error regions, and narrow-screen stacking. File-removal focus can be lost in one case (UX-2). |

## Findings

### UX-1 — Generic HTTP 400 handling throws instead of reporting the server error

- **Severity:** MEDIUM
- **Evidence:** `src/main/resources/web/app.js:455-458` calls `focusWhenReady(elements.picker)` from `handleFailure`. `focusWhenReady` is declared only inside `showFieldError` (`app.js:311-314`), so it is not in scope here.
- **User impact:** A generic API validation response raises a `ReferenceError` while being handled. The enclosing `submitOperation` catch then replaces the useful validation feedback with “Impossibile raggiungere l'applicazione locale,” falsely suggesting the server is unreachable.
- **Recommendation:** Use a shared focus helper or call the picker’s focus method directly, and verify a generic 400 response leaves the selected work intact and displays the validation message.

### UX-2 — Removing the final/last-position file drops keyboard focus

- **Severity:** LOW
- **Evidence:** `src/main/resources/web/app.js:168-172` re-renders with no focus target when the removed index is not less than the new list length. Removing the only item or the final item therefore removes the focused button without moving focus elsewhere.
- **User impact:** Keyboard and screen-reader users lose their place after removing the last item.
- **Recommendation:** After removal, focus the next item’s remove control, the previous item when there is no next item, or the file picker when the list becomes empty.

### UX-3 — Error result keeps the success checkmark and green styling

- **Severity:** LOW
- **Evidence:** `src/main/resources/web/index.html:182-188` always renders the green check icon in the result heading; error handling changes text but not the icon/state styling.
- **User impact:** The success symbol can contradict the adjacent error alert.
- **Recommendation:** Switch the result icon/styling according to success, error, and in-progress state, or use a neutral icon for the shared result heading.

## Conformance and Validation

- All five operations and the shared file-selection/download model are represented in the implementation.
- Accessibility requirements are substantially implemented: semantic headings and fieldsets, keyboard-operable ordering controls, visible focus, field descriptions, `role=status`, and `role=alert` are present.
- Source inspection confirms that most operation-level validation is handled before submission and that the frontend maps expected 400/413/415/422 responses to localized feedback. UX-1 is specifically the generic 400 fallback.
- The t5 frontend report records `mvn -B clean test package` passing (2 passed, 0 failed, 0 skipped), endpoint probes, and headless Chrome workflow checks including mobile reflow. These are inherited evidence; t8 did not independently launch the application or rerun tests.
- `context.md`, `decisions.md`, and `team/ux/inbox.md` were not present in the workspace; the available board and dependency artifacts supplied the task scope and review baseline.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/board.md` — user-selected localhost-only scope and preservation expectations.
- `.github/modernize/rearchitecture/artifacts/t2-ux.md` — expected operation journeys, selection behavior, feedback, and accessibility bar.
- `.github/modernize/rearchitecture/artifacts/t5-frontend.md` — implemented workflow summary and prior browser-validation evidence.
- `.github/modernize/rearchitecture/artifacts/t5-frontend-batch-report.yaml` — changed-file list and recorded build/browser checks.
- `.github/modernize/rearchitecture/artifacts/t4-backend-implementation.md` — endpoint errors, result formats, and operation behavior used to assess recovery feedback.
- `.github/modernize/rearchitecture/artifacts/units/pdf-workbench/behavior.yaml` and `.github/modernize/rearchitecture/artifacts/wire_contracts.yaml` — legacy behavior and expected request/response contracts.
- `.github/modernize/rearchitecture/learnings/ux/localhost-pdf-workbench.md` — ordered visible selection, operation cardinality/settings, and original-file preservation guidance.

## Evidence Mapping

- `t2-ux.md#Operation workflows and controls` and `behavior.yaml#branches,side_effects` → workflow preservation table above, checked against `index.html` and `app.js`.
- `t2-ux.md#Shared interaction and feedback rules` and `wire_contracts.yaml#Split PDF,Merge PDFs,Rename PDFs,Encrypt PDFs,Extract text` → response/error review and finding UX-1 in `app.js`.
- `t2-ux.md#Accessibility requirements` → keyboard and live-region review; finding UX-2 maps to the specified keyboard-operable selection/removal flow.
- `t5-frontend-batch-report.yaml#browser_validation,test_results` → prior runtime evidence summarized under Conformance and Validation; no independent t8 test run is claimed.
