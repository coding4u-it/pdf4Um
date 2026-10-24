# Browser Tool Evidence

When an integrated browser automation tool exposes no operating-system exit code, record its native execution result and assertion evidence without inventing a numeric process code.

## What Happened

In `pdf4Um` task t11.1, a prior runtime report marked browser E2E `exit_code: 0` while noting that the integrated browser tool exposed no process code. The strategy now distinguishes shell-runner return codes from native browser-tool completion status and requires actual assertion outcomes for each journey.

## Takeaway

For direct browser-tool invocations, report the tool's own success/failure signal and flow/assertion counts. Only report an OS exit code when a spawned process actually provides it. Keep the browser-tool evidence separate from HTTP integration coverage.

## History
- 2026-10-24 (pdf4Um/t11.1): initial

