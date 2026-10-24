# t4 — Backend implementation details

## Server and route boundary

`com.mycompany.pdf4um.Main` is now the web application entrypoint, preserving the FQCN referenced by existing run actions. It starts a JDK `HttpServer` bound explicitly to `127.0.0.1`; the default port is `8080`, configurable through `-Dpdf4um.port=<port>`. There is no CORS configuration, remote bind option, server-side path parameter, or persistent request session.

| Route | Behavior | Successful response |
|---|---|---|
| `GET /` | Serves bundled `web/index.html` | HTML page |
| `GET /app.js`, `/styles.css` | Serves the two allowlisted UI assets | JavaScript / CSS |
| `POST /api/split` | One `file`; optional positive `pagesPerPart`, default one page | ZIP of numbered PDF parts |
| `POST /api/merge` | At least two repeated `files`, in submitted order | PDF attachment named `<first-stem>_merged.pdf` |
| `POST /api/rename` | Repeated `files`, sequential or random mode | ZIP of renamed copies; random mode includes `esporta.csv` |
| `POST /api/encrypt` | Repeated `files`, required password and permission flags | ZIP of protected PDF copies |
| `POST /api/extract-text` | One `file` | UTF-8 `<stem>_text.txt` attachment |

All operation requests are `multipart/form-data`. The server enforces a 100 MiB total request-body limit and a maximum of 32 PDFs per workflow (40 multipart parts, including form fields). It sanitizes client filenames, accepts uploaded PDF bytes rather than client paths, validates inputs with PDFBox, and maps validation/media/PDF failures to 400/415/422. Unexpected failures return a generic 500 JSON error without filesystem paths or stack traces.

Each operation gets its own `Pdf4UmController` and `Pdf4UmModel` and a fresh temporary directory. Outputs are streamed as attachments before that directory is removed. Rename writes copies and keeps the random-mode CSV inside the response ZIP; selected originals are never modified. `FileOperazioni` now takes explicit destinations instead of deriving output paths from the process working directory. PDF encryption retains the existing 256-bit policy and permission-flag mapping; `PdfTools` closes the loaded document with try-with-resources.

## Preserved behavior

- Split-all defaults to one page per output; group split requires a positive page count and retains the `_0001.pdf` numbering style.
- Merge requires two PDFs and preserves browser selection order and the first file's stem.
- Sequential rename retains prefix plus incrementing number. Random rename retains configured code length/symbol option and the legacy `.pdf;code` CSV rows, now packaged instead of written to CWD.
- Encryption retains the existing 256-bit StandardProtectionPolicy, owner password `password + password`, user password `password`, `_cript.pdf` suffix, and existing permission inversion behavior.
- Text extraction continues to use PDFBox `PDFTextStripper` and returns UTF-8 text as a download with `_text.txt` suffix.
- The browser upload/download boundary leaves source files untouched.

## Exact changed project files

- `README.md` — localhost start/browser/port instructions and upload limits.
- `pom.xml` — JUnit 4.13.2 test-scoped dependency.
- `src/main/java/com/mycompany/pdf4um/Main.java` — retained-FQCN server bootstrap.
- `src/main/java/com/mycompany/pdf4um/controller/Pdf4UmController.java` — stateless, explicit-input workflow coordination.
- `src/main/java/com/mycompany/pdf4um/model/FileOperazioni.java` — explicit-path copy/text-output helpers.
- `src/main/java/com/mycompany/pdf4um/model/Pdf4UmModel.java` — workspace-safe rename copies and text extraction result.
- `src/main/java/com/mycompany/pdf4um/model/PdfTools.java` — closes the encrypted document deterministically; no eager unused blank PDF document allocation.
- `src/main/java/com/mycompany/pdf4um/web/MultipartFormData.java` — bounded multipart parser.
- `src/main/java/com/mycompany/pdf4um/web/Pdf4UmWebServer.java` — loopback server, allowlisted static resources, endpoints, errors, downloads, and workspace cleanup.
- `src/test/java/com/mycompany/pdf4um/web/Pdf4UmWebServerTest.java` — endpoint integration and behavior tests.

No `.vscode/launch.json` changes were made. Existing unrelated worktree modifications were left untouched.

## Test Results

- `mvn -B clean test package` — passed; 2 tests, 0 failures, 0 errors, 0 skipped.
- The integration tests use an ephemeral HTTP port and asserted `127.0.0.1`, and received HTTP 200 for all five PDF operations.
- Test command: `mvn -B clean test package`
- Passed: 2
- Failed: 0
- Skipped: 0
- Failures: none.

## Runtime Verification and Integration Limits

- The packaged JAR was launched with `-Dpdf4um.port=28763`; `ss` reported `[::ffff:127.0.0.1]:28763`, and `curl http://127.0.0.1:28763/` reached the application. That request returned 503 because the frontend resource task had not yet added its three bundled assets; the backend's REST workflow endpoints were exercised successfully by the HTTP integration tests.
- The existing Maven build warns that `maven-jar-plugin` has no pinned version and that Java 11 source/target are compiled without an explicit system-modules path. Those pre-existing build configuration warnings remain unchanged.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t1-architect.md` — route and boundary design navigation.
- `.github/modernize/rearchitecture/artifacts/wire_contracts.yaml` — concrete route, payload, response, and error contracts.
- `.github/modernize/rearchitecture/artifacts/migration_boundary.yaml` — implementation scope, loopback requirement, temporary workspace, and launch-config preservation.
- `.github/modernize/rearchitecture/artifacts/units/pdf-workbench/behavior.yaml` — source workflow branches and side effects.
- `.github/modernize/rearchitecture/artifacts/units/pdf-workbench/bindings.yaml` — Swing-to-browser binding replacement.
- `.github/modernize/rearchitecture/artifacts/project-structure.md` — source layers and existing main class.
- `.github/modernize/rearchitecture/artifacts/t3-devops.md` — active Java/Maven runtime.
- `.github/modernize/rearchitecture/learnings/architect/localhost-pdf-web-boundary.md` — request workspace and loopback guidance.

## Evidence Mapping

- `wire_contracts.yaml#POST /api/split` → split route and ZIP download → integration test verifies 200 and `_0001.pdf` outputs.
- `wire_contracts.yaml#POST /api/merge` → ordered PDF merge route → integration test verifies 200 and merged page count/order.
- `wire_contracts.yaml#POST /api/rename` → copy-based sequential/random modes → integration test verifies names and legacy CSV rows.
- `wire_contracts.yaml#POST /api/encrypt` → encryption route → integration test opens encrypted output with submitted user password.
- `wire_contracts.yaml#POST /api/extract-text` → PDFTextStripper attachment → integration test verifies extracted content.
- `migration_boundary.yaml#implementation_rule` → request-scoped workspace and no source-file mutations → implementation plus completed endpoint tests.
- `board.md#User Input` → fixed 127.0.0.1 bind and retained launch FQCN → test assertion and packaged-JAR loopback listener probe.
