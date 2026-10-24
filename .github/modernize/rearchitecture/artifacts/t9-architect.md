# t9 — Localhost Build and Startup Smoke Test

## Verdict

**PASS.** The full Maven verification completed successfully. The packaged Java application started in 178 ms, bound to the IPv4 loopback address, and served the browser workbench and its static assets with HTTP 200 responses. The application process was stopped after verification. No project source or configuration files were changed by this task.

## Smoke Test Verdict
- install_command: `n/a for non-JS/TS`
- install_returncode: n/a
- build_command: `mvn -B clean verify`
- returncode: 0
- covers_all_modules: yes
- startup_http_status: 200
- test_script_present: n/a
- test_returncode: n/a

## Build and Test Results

- Full build: `mvn -B clean verify` — exit code 0 (`BUILD SUCCESS`).
- Tests: 2 passed, 0 failed, 0 errors, 0 skipped.
- The tests ran `Pdf4UmWebServerTest`, covering loopback binding and successful behavior for all five PDF workflows.
- Maven emitted existing warnings for the unpinned `maven-jar-plugin` version and compiling Java 11 source/target without an explicit system-modules path. These did not fail the build.

## Startup and HTTP Evidence

- Start command: `java -Dpdf4um.port=28763 -jar target/Pdf4Um-1.0-SNAPSHOT-jar-with-dependencies.jar`
- Startup time to first successful root response: **178 ms**.
- Listener: `ss -ltnp` reported `[::ffff:127.0.0.1]:28763` (IPv4-mapped loopback).
- `GET http://127.0.0.1:28763/` — HTTP 200, remote address `127.0.0.1`.
- `GET http://127.0.0.1:28763/app.js` — HTTP 200.
- `GET http://127.0.0.1:28763/styles.css` — HTTP 200.
- The server was stopped after these probes; no long-running process was left behind.

## Files and Worktree

- Application source/configuration changes made by t9: none.
- Deliverable: `.github/modernize/rearchitecture/artifacts/t9-architect.md`.
- Session log updated: `.github/modernize/rearchitecture/team/architect/log.md`.
- The pre-existing `.vscode/launch.json` remains unmodified and untracked.
- No commit was created.

## Upstream Artifacts Consumed

- `.github/modernize/rearchitecture/artifacts/t4-backend.md` — server entry point, loopback port, route inventory, prior test evidence.
- `.github/modernize/rearchitecture/artifacts/t4-backend-implementation.md` — exact packaged-JAR invocation and runtime behavior.
- `.github/modernize/rearchitecture/artifacts/t5-frontend.md` — expected root and static resources and browser workflow scope.
- `.github/modernize/rearchitecture/artifacts/t5.1-frontend.md` — final browser error/focus fixes and frontend verification.
- `.github/modernize/rearchitecture/artifacts/t6-backend.md` — dependency scan and prior full Maven verification.
- `.github/modernize/rearchitecture/artifacts/t3-devops.md` — available Java/Maven runtime.
- `.github/modernize/rearchitecture/artifacts/t7-architect.md` — reviewed loopback-only design and route/test conformance.
- `.github/modernize/rearchitecture/board.md` — localhost-only user requirement and instruction to preserve existing worktree changes.

## Evidence Mapping

- `t4-backend-implementation.md#Server and route boundary` → packaged-JAR launch at the documented port → measured readiness in 178 ms; `ss` reported the loopback-only listener.
- `t5-frontend.md#Deliverables` and `t5.1-frontend.md#Files Changed` → UI resource paths → root, JavaScript, and stylesheet returned HTTP 200.
- `t4-backend.md#Test Results` and `t6-backend.md#Outcome` → full build/test verification → `mvn -B clean verify` exited 0 with 2 tests passed and none failed.
- `board.md#User Input` → preserve localhost-only operation and the existing launch config → runtime listener was loopback; `.vscode/launch.json` remained untouched.

## Issues and Limitations

- Findings: 0 HIGH, 0 CRITICAL.
- No blocker. Existing Maven configuration warnings are recorded above.
- Runtime HTTP probes covered UI and static assets; PDF operation behavior was covered by the two integration tests, not re-exercised manually during this smoke-test task.
