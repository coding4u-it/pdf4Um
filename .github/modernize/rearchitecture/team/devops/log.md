## [t3] Prepared local Java/Maven/browser runtime evidence
- Codebase/domain discoveries: Maven already targets Java source/bytecode 11; current shell resolves OpenJDK 21.0.12.1 and Maven 3.9.12. Chrome 156 headless works. No test sources exist yet.
- Wrong assumptions and corrections: A passing Maven test lifecycle currently means compilation/build success only; there are no tests to execute. `JAVA_HOME` is unset.
- Debugging dead-ends and what actually worked: Chrome's headless `--dump-dom` verified browser rendering without requiring a UI session. Docker daemon was unavailable; not required for this app's current local runtime.
- Techniques/patterns worth reusing: Record the specific JDK active in PATH separately from the compiler target. Avoid assuming `JAVA_HOME`, Node/Playwright, or a web-server port/entry point before implementation.
- Learnings consumed: []
