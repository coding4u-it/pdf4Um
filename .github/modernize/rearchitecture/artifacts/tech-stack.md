# Existing Technology Stack

- Language: Java.
- Declared source/target compatibility: Java 11 (`pom.xml`).
- Observed local runtime during inspection: OpenJDK 21.0.12.1; Maven 3.9.12.
- Build: Maven, single module, coordinates `com.mycompany.pdf4um:Pdf4Um:1.0-SNAPSHOT`.
- PDF library: `org.apache.pdfbox:pdfbox:2.0.26`.
- UI: Java Swing/AWT.
- Plugins: Maven Dependency Plugin copies dependencies into `target/libs`; Maven JAR Plugin sets `com.mycompany.pdf4um.Main`; Maven Assembly Plugin builds a `jar-with-dependencies`.
- Tests: no `src/test` files were found during this task.
- Persistence/network integrations: none in the current source.

The architecture design recommends using the JDK's `com.sun.net.httpserver` for the small loopback web boundary to avoid introducing a full framework; this is a target design decision, not an existing dependency. Ensure the selected build/run path includes the JDK `jdk.httpserver` module. Do not silently raise the Java language target above the user's existing Java 11 baseline.
