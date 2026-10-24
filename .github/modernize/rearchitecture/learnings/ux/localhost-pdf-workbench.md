# Localhost PDF Workbench UX

For browser replacements of local PDF utilities, preserve an ordered visible file selection, make operation-specific file counts and settings explicit, and keep uploaded originals untouched.

## What Happened

In `pdf4Um` task t2, the Swing UI showed selected filenames, allowed clearing the selection, and exposed five workflows. The browser specification retained those affordances while replacing local-path assumptions with upload-and-download interactions. It also avoided carrying a visible fixed default password into the web form.

## Takeaway

Use one responsive workbench with an ordered, keyboard-operable file list; disclose per-operation cardinality and naming; retain selection and non-secret values on errors; clear secrets after processing; announce progress and downloads accessibly.

## History
- 2026-10-24 (pdf4Um/t2): initial
