# Localhost PDF Web Boundary

For a browser migration of a desktop Java PDF tool, keep the server loopback-bound and treat every browser file as uploaded bytes in an isolated temporary workspace.

## What Happened

In `pdf4Um` task t1, inspection showed that the Swing file chooser selected local files and downstream helpers wrote outputs beside those originals; random rename also wrote `esporta.csv` to process CWD. A web browser cannot safely provide server-readable client paths. The architecture therefore uses uploads and attachment downloads, preserves the current `Main` FQCN for existing launch configurations, and requires per-request operation state or serialization because controller/PDF helper objects are mutable.

## Takeaway

For local-only Java file-processing apps, bind explicitly to `127.0.0.1`, serve UI/API from one origin, accept bounded uploads rather than path strings, write all operation output inside request-scoped temporary storage, and return results as downloads. Never expose an existing desktop helper's implicit working-directory writes directly through a web route.

## History
- 2026-10-24 (pdf4Um/t1): initial
