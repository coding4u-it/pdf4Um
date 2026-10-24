# Current Project Structure

## Classification

Single-module Java desktop application (Swing UI plus PDF processing), not currently a web backend, frontend, library, CLI, or monorepo. The project profile reports approximately 1,278 LOC; the checked-in Java production tree contains one application entrypoint, one controller, three model/helper classes, and image assets.

## Packages and layers

- `com.mycompany.pdf4um`
  - `Main.java`: Swing `JFrame`, controls, menu actions, file chooser, and `main` entrypoint.
  - `Main.form`: NetBeans GUI form metadata for the Swing window.
- `com.mycompany.pdf4um.controller`
  - `Pdf4UmController.java`: selected-file/password state, operation validation, and delegation to the model.
- `com.mycompany.pdf4um.model`
  - `Pdf4UmModel.java`: operation coordination, rename/export flow, PDF tools and file-helper composition.
  - `PdfTools.java`: PDFBox split, merge, encryption, and text extraction; also contains two additional PDF-specific methods not invoked by the current menu.
  - `FileOperazioni.java`: local rename and text/CSV file I/O helpers.
  - `Critografia.java`: random rename-code generation.
- `com.mycompany.img`
  - PNG icons used by the UI.

The effective runtime flow is `Main` → `Pdf4UmController` → `Pdf4UmModel` → PDFBox/file helpers. No persistence, database, external service, or multi-module boundary was found.

## Entry points and configuration

- `com.mycompany.pdf4um.Main.main` launches the Swing frame (`Main.java:806`).
- `pom.xml` sets Java source/target 11, declares PDFBox 2.0.26, and assembles executable JARs.
- `nbactions.xml` uses the same `Main` class for run/debug/profile.
- `.vscode/launch.json` is an existing untracked Java launch configuration for `com.mycompany.pdf4um.Main`; preserve it. Keeping this class FQCN as the new web entrypoint permits the configuration to remain valid.
- `README.md` currently documents only Swing/Maven build instructions and must be updated by the implementation phase to explain localhost startup.

## Existing externally visible workflows

1. Select one or more local PDF files; selected names appear in the UI.
2. Split one PDF into individual pages (default) or groups of a requested positive page count.
3. Merge at least two PDFs into a file named from the first source plus `_merged.pdf`.
4. Rename one or more PDFs sequentially or with random suffixes; random mode also emits `esporta.csv`.
5. Encrypt one or more PDFs with a password and five permission controls; output files use `_cript.pdf`.
6. Extract text from one PDF into a sibling `_text.txt` file.

The browser boundary must adapt file selection to uploads and generated files to downloads; server-side path access is not available from a browser and is not part of the web API.
