# t3 — Local Java/Maven/Browser Runtime Preparation

## Summary

The active environment is ready to build the existing Java project and run a browser against a local page. No application launch command or port can be finalized yet: the web-server implementation and its entry point are downstream work. The server must bind only to `127.0.0.1` to honor the user's localhost-only requirement.

## Target Environment Preparation

- **Status:** READY for Java/Maven builds and local browser use; browser automation tooling is not ready.
- **Requested target versions:** No new runtime version was specified. Existing `pom.xml` compiler source/target are Java 11.
- **Preparation actions taken:** Inspected the existing Maven configuration; verified test and package lifecycles; verified headless Chrome can render a local page. No system packages, project dependencies, launch configuration, or environment defaults were changed.
- **Installed versions:**
  - Java runtime: OpenJDK 21.0.12.1, `/usr/bin/java`
  - Java compiler: `javac 21.0.12.1`, `/usr/bin/javac`
  - Maven: Apache Maven 3.9.12, `/usr/bin/mvn`
  - Google Chrome: 156.0.8078.47, `/usr/bin/google-chrome`
  - Firefox: executable resolves to `/usr/bin/firefox`; a usable version was not confirmed because its version command emitted a Snap mount-namespace warning.
- **Active default versions:** Java 21.0.12.1 and Maven 3.9.12 resolve through `/usr/bin`; `JAVA_HOME` is unset.
- **Command-resolution evidence:** `command -v java` → `/usr/bin/java`; `command -v javac` → `/usr/bin/javac`; `command -v mvn` → `/usr/bin/mvn`; `google-chrome --version` → `Google Chrome 156.0.8078.47`.
- **Version planned build/test commands will use:** The default Java 21 runtime/compiler and Maven 3.9.12. The existing Maven compiler configuration targets Java 11 bytecode/source compatibility; there is no Java 11 installation selected by the shell.
- **Exact activation commands/env vars downstream tasks must use:** None required for the available build tools. `JAVA_HOME` is unset; do not assume it is configured. To make activation explicit in a shell, use `export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64` and ensure `/usr/lib/jvm/java-21-openjdk-amd64/bin` precedes other JDKs on `PATH`.
- **Browser use:** `google-chrome --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --dump-dom '<local URL>'` works in this environment. Open the eventual application at the exact `127.0.0.1` URL/port selected by its implementation; no server port exists yet.
- **Missing tools:** Node.js, npm, npx, and Docker are unavailable (Docker daemon did not respond to `docker info`). Node is not required to run the Java web application, but is required for Playwright-based browser tests. Chrome is installed; Playwright itself is not.
- **Blockers:** None for compiling/package-building the current project or serving a Java application to a local browser. Playwright browser automation is blocked on Node.js/Playwright installation. Docker-dependent infrastructure is unavailable and should not be introduced for this local-only app without a requirement.
- **Downstream implications:** Keep the Java/PDFBox implementation and its build on Maven; choose an explicit, stable JDK target consistent with the project's existing Java 11 source/target unless the architecture task documents otherwise. Add an explicit localhost bind address and document the real start command and port once chosen. README currently documents the Swing app and its Java entry point, so the implementation owner should replace that guidance with the verified web launch/browser instructions when the server entry point is finalized. Preserve `.vscode/launch.json`; it is an existing untracked worktree addition and still targets the desktop `Main` class, so do not silently repurpose or delete it.

## Upstream Artifacts Consumed

- none — no dependency artifacts provided

## Evidence Mapping

- none — no dependency artifacts provided

## Test Results

- `mvn -B test` — passed (build success; 0 test sources found, 0 tests executed, 0 failures, 0 skipped).
- `mvn -B package` — passed; produced `target/Pdf4Um-1.0-SNAPSHOT.jar` and `target/Pdf4Um-1.0-SNAPSHOT-jar-with-dependencies.jar`.
- `google-chrome --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --dump-dom 'data:text/html,<title>pdf4Um-browser-check</title><p>ready</p>'` — passed; Chrome returned rendered HTML containing the expected title and body.
- Maven emitted a warning that the `maven-jar-plugin` version is not pinned. This is existing build configuration; it was not changed in this environment-preparation task.
- No localhost application endpoint was started or probed because the web server is not implemented yet.
