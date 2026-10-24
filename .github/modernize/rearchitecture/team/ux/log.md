## [t2] Specified browser workbench workflows
- Codebase/domain discoveries: the current Swing UI presents Italian labels, multi-file selection with a visible filename list, a clear action, five PDF operations, and conditional controls for split and rename.
- Wrong assumptions and corrections: the old visible password default `1234` should not be carried into the web workflow; make the password explicitly required and initially blank.
- Debugging dead-ends and what actually worked: the t1 index plus its behavior, bindings, and wire-contract files provided enough operation semantics; direct UI source inspection filled in labels and interaction details.
- Techniques/patterns worth reusing for future tasks: maintain a visible ordered selection list, make merge order explicit and keyboard-adjustable, and preserve user work after errors while treating outputs as downloads.
- Learnings consumed: [architect/localhost-pdf-web-boundary]

## [t8] Reviewed browser workflow preservation and usability
- Codebase/domain discoveries: the browser workbench represents all five required PDF operations and prior frontend evidence covers core settings and narrow-screen reflow; generic HTTP 400 handling references a helper outside its scope, and removing the last file drops focus.
- Wrong assumptions and corrections: no independent runtime verification was performed for t8; the browser/build results in the report are cited as t5 evidence only.
- Debugging dead-ends and what actually worked: line-level source review plus t2 workflow requirements and t5 report identified the generic error fallback and keyboard focus gap without changing frontend source.
- Techniques/patterns worth reusing for future tasks: review both successful flows and failure/focus recovery; ensure shared focus helpers are actually in scope and result-state indicators match the outcome.
- Learnings consumed: [ux/localhost-pdf-workbench]
