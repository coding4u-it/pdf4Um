## User Input

> Implement a structural Java desktop MVC refactor of the existing repository. Inspect the project and working tree first; preserve any unrelated pre-existing dirty changes. Keep the existing Java language, framework, UI, and behavior. Make a surgical but complete MVC separation, update directly related docs if any, and run focused validation/build/tests. Do not modify unrelated areas or ask clarification. Workspace: /home/france/gitHub/pdf4Um

**Project started**: 2026-10-22T17:01:47Z

## Tasks

### Phase: Analysis
- ⏳ t1 [architect] Analyze current desktop application structure and MVC boundaries

### Phase: Design
- ⏳ t2 [architect] Define a surgical MVC refactor preserving existing behavior [deps: t1]

### Phase: Implementation
- ⏳ t3 [frontend] Implement the MVC separation and update directly related documentation [deps: t2]

### Phase: Architecture Review
- ⏳ t4 [architect] Review implementation against the MVC design [deps: t3]

### Phase: Smoke Test
- ⏳ t5 [architect] Build and launch the application independently [deps: t3]

### Phase: Runtime Validation
- ⏳ t6 [tester] Run focused regression tests and report validation evidence [deps: t4, t5]
