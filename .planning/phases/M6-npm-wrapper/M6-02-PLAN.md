---
phase: M6-npm-wrapper
plan: 02
type: execute
wave: 2
depends_on: ["M6-01"]
files_modified:
  - npm/bin/voss.js                    # REPLACE (real shim; M6-01 only stubbed)
  - npm/platforms/darwin-arm64/package.json  # AMEND (description/keywords; postinstall stays)
  - npm/platforms/darwin-x64/package.json    # AMEND
  - npm/platforms/linux-x64/package.json     # AMEND
  - npm/platforms/linux-arm64/package.json   # AMEND
  - npm/platforms/win32-x64/package.json     # AMEND
autonomous: true
requirements: [NPM-03]
must_haves:
  truths:
    - "`node npm/bin/voss.js --help` on a host with a pre-built platform subpackage available exits 0 and prints the voss help text"
    - "The shim spawns the vendored Python at the per-platform path branched on `process.platform === 'win32'` (Unix: `python/bin/python3`; Windows: `python/python.exe`)"
    - "The shim invokes `python -m voss.cli` with all argv after `argv[2]` forwarded, `shell: false`, `stdio: 'inherit'`"
    - "Exit code from the Python child is preserved (0, 1, or any subcommand-specific code)"
    - "On Unix, SIGINT during a long-running child causes the shim to exit 130 (128 + signal=2)"
    - "Unknown platform/arch combinations exit 1 with a clear stderr message naming the unsupported pair"
    - "Missing platform subpackage (e.g. `--ignore-optional` install) exits 1 with a stderr message telling the user which `@voss/cli-*` package to install"
  artifacts:
    - path: "npm/bin/voss.js"
      provides: "Node bin shim per RESEARCH §6 Biome pattern; spawns vendored Python -m voss.cli"
      min_lines: 50
      contains: "spawnSync"
  key_links:
    - from: "npm/bin/voss.js"
      to: "@voss/cli-<platform>-<arch>"
      via: "require.resolve(`${pkg}/package.json`)"
      pattern: "require\\.resolve"
    - from: "npm/bin/voss.js"
      to: "vendored python binary"
      via: "path.join(pkgDir, 'python', isWindows ? 'python.exe' : 'bin/python3')"
      pattern: "python\\.exe|bin/python3"
    - from: "npm/bin/voss.js"
      to: "voss CLI module"
      via: "spawn args ['-m', 'voss.cli', ...argv]"
      pattern: "'-m',\\s*'voss\\.cli'"
---

<objective>
M6-02 replaces the M6-01 stub shim with the real Node.js bin shim per RESEARCH §6 (Biome pattern). The shim's job is single-purpose: resolve the platform subpackage that npm's optionalDependencies machinery installed on this host, locate the vendored Python interpreter inside it, and spawn `python -m voss.cli` with full argv/stdio/exit-code/signal forwarding.

Purpose: NPM-03 directly demands "preserves exit codes, stdin/stdout/stderr, and signal forwarding". Without this shim there is no CLI surface, just an empty package manifest. The shim is also the only piece of new executable code in the entire M6 phase — everything else is build scripts, CI workflows, and tests. Getting this right is load-bearing for every downstream smoke test in M6-05.

Output: A ~70-line `npm/bin/voss.js` file that can be exercised with `node npm/bin/voss.js --help` once any one platform subpackage is built locally (M6-03's job). This plan does not download PBS or build a subpackage; it implements only the shim. Validation of NPM-03 against a real built platform happens in M6-05.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M6-npm-wrapper/M6-RESEARCH.md
@.planning/phases/M6-npm-wrapper/M6-PATTERNS.md
@.planning/phases/M6-npm-wrapper/M6-CONTEXT.md
@.planning/phases/M6-npm-wrapper/M6-01-PLAN.md
@npm/bin/voss.js
@npm/package.json

<interfaces>
<!-- Behavioral contracts the shim must honor. The shim has no in-repo analog — these are
     extracted from RESEARCH §6 (Biome pattern) and the Node child_process docs cited there.
     The shim is a pure dispatcher; it imports nothing from voss/* — argv is forwarded
     verbatim to the vendored python which then loads voss.cli itself. -->

Node.js child_process.spawnSync return shape (relevant subset):
- result.status: number | null  // child's exit code; null if killed by signal
- result.signal: string | null  // e.g. 'SIGINT', 'SIGTERM'
- result.error: Error | undefined  // failed to spawn (ENOENT etc.)

Exit-code conventions enforced by the shim:
- result.status (number)            → process.exitCode = result.status
- result.signal === 'SIGINT'        → process.exitCode = 130   // 128 + 2
- result.signal === 'SIGTERM'       → process.exitCode = 143   // 128 + 15
- result.signal === any other       → process.exitCode = 128
- result.error truthy               → throw (Node prints stack, exits 1)

Platform dispatch table (from RESEARCH §6):
- PLATFORMS[process.platform][process.arch] → '@voss/cli-<platform>-<arch>'
- Supported pairs (D-13): darwin/arm64, darwin/x64, linux/arm64, linux/x64, win32/x64
- Any other pair → exit 1 with message "voss: unsupported platform: <plat> <arch>"

Python invocation contract:
- Args: [pythonBin, '-m', 'voss.cli', ...process.argv.slice(2)]
- Options: { shell: false, stdio: 'inherit', env: process.env }
- Pythonbin: $pkgDir/python/python.exe (win32) or $pkgDir/python/bin/python3 (unix)

From pyproject.toml: `[project.scripts] voss = "voss.cli:main"` — the `-m voss.cli` module
form is equivalent and is used here (per CONTEXT.md "JS shim's spawn target is exactly
python -m voss.cli (use the module form so it works even if console-script symlink is missing)").
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write the bin shim with platform dispatch + signal handling</name>
  <files>npm/bin/voss.js</files>
  <read_first>
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §6 entire section (Bin Shim Design)
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §10 "Cross-Platform Gotchas" Windows subsection
    - .planning/phases/M6-npm-wrapper/M6-CONTEXT.md D-02 (50 LOC Node JS shim)
    - .planning/phases/M6-npm-wrapper/M6-PATTERNS.md "npm/bin/voss.js (utility, request-response)"
    - voss/cli.py (just the module header — confirm `main` is the entry point; the shim does NOT import this)
  </read_first>
  <behavior>
    - Test 1: shim with no subpackage installed exits 1 with stderr matching `/platform package @voss\/cli-.* not installed/`.
    - Test 2: shim on a fabricated supported platform (mock require.resolve) spawns the python binary at the expected path with args `['-m', 'voss.cli', '--help']` when argv is `['--help']`.
    - Test 3: shim on an unsupported platform/arch combo (e.g. linux/ppc64le) exits 1 with stderr matching `/unsupported platform: linux ppc64le/`.
    - Test 4: when spawnSync returns `{ status: 1 }`, the shim sets `process.exitCode = 1`.
    - Test 5: when spawnSync returns `{ status: null, signal: 'SIGINT' }`, the shim sets `process.exitCode = 130`.

    Test 1, 3, 4, 5 should run under Node test runner against a small wrapper that monkey-patches `child_process.spawnSync` and `require.resolve`. Test 2's full-spawn check is deferred to M6-05's pytest smoke (it needs a real PBS extract). At minimum the unit tests in this plan cover Tests 1, 3, 4, 5.
  </behavior>
  <action>
    Implement `npm/bin/voss.js` end-to-end, replacing the M6-01 stub. The file structure (~70 LOC):

    1. `#!/usr/bin/env node` shebang on line 1.
    2. `'use strict';` on line 2.
    3. Require `child_process.spawnSync`, `path`, `fs`.
    4. Define `PLATFORMS = { darwin: { arm64: '@voss/cli-darwin-arm64', x64: '@voss/cli-darwin-x64' }, linux: { arm64: '@voss/cli-linux-arm64', x64: '@voss/cli-linux-x64' }, win32: { x64: '@voss/cli-win32-x64' } }`.
    5. `findPlatformPackage()` function: read `process.platform` and `process.arch`; look up in PLATFORMS; if undefined → `process.stderr.write('voss: unsupported platform: ' + platform + ' ' + arch + '\n')` then `process.exit(1)`. If found, wrap `require.resolve(pkg + '/package.json')` in try/catch; on catch, stderr-write `'voss: platform package ' + pkg + ' not installed.\nTry: npm install ' + pkg + '\n'` and exit 1. On success, return the package dir via `path.dirname` of the resolved path.
    6. Compute `isWindows = process.platform === 'win32'`.
    7. Compute `pythonBin = isWindows ? path.join(pkgDir, 'python', 'python.exe') : path.join(pkgDir, 'python', 'bin', 'python3')`.
    8. Guard with `fs.existsSync(pythonBin)`; if absent, stderr-write `'voss: vendored Python not found at ' + pythonBin + '\n'` and exit 1.
    9. Call `spawnSync(pythonBin, ['-m', 'voss.cli', ...process.argv.slice(2)], { shell: false, stdio: 'inherit', env: process.env })`.
    10. Result handling: if `result.error` → `throw result.error`. If `result.signal` truthy → map to exit code (`SIGINT`→130, `SIGTERM`→143, other→128) and set `process.exitCode`. Else `process.exitCode = result.status`.

    Do NOT add: a `process.on('SIGINT', ...)` handler (spawnSync with stdio:inherit already routes the signal to the child via the shared terminal process group — RESEARCH §6 "Signal forwarding semantics"). Do NOT add: a `--version` shortcut. Do NOT add: any caching, telemetry, or post-success printing. The shim must remain ~70 LOC.

    Also: amend each of the 5 `npm/platforms/<triple>/package.json` files written by M6-01 to add `"description"` (e.g. `"Voss CLI vendored binaries — darwin arm64"`), `"keywords": ["voss", "cli", "ai", "coding"]`, and `"author"` (same as main package). Do NOT change `os`, `cpu`, `files`, `name`, `version`, or `postinstall` from what M6-01 wrote. The amendment exists to keep `npm publish` warnings quiet in M6-04.

    Mark `npm/bin/voss.js` executable (`chmod +x`) so the bit survives git commit and `npm pack`. Verify executable bit with `ls -l`.
  </action>
  <verify>
    <automated>node -e "const fs=require('fs'); const c=fs.readFileSync('npm/bin/voss.js','utf8'); const checks=[c.startsWith('#!/usr/bin/env node'), c.includes(\"'use strict'\"), c.includes('spawnSync'), c.includes(\"stdio: 'inherit'\")||c.includes('stdio:\"inherit\"'), c.includes('shell: false')||c.includes('shell:false'), c.includes(\"'-m', 'voss.cli'\")||c.includes('\"-m\",\"voss.cli\"'), c.includes('process.platform'), c.includes('process.arch'), c.includes('python.exe'), c.includes('bin/python3'), c.includes('SIGINT'), c.match(/PLATFORMS|platforms\\s*=/), c.split('\\n').length&lt;120]; if(!checks.every(Boolean)){console.error('checks:',checks);process.exit(1);} const st=fs.statSync('npm/bin/voss.js'); if(!(st.mode &amp; 0o111)){console.error('not executable');process.exit(1);} console.log('ok');" &amp;&amp; for p in darwin-arm64 darwin-x64 linux-x64 linux-arm64 win32-x64; do node -e "const m=require('./npm/platforms/$p/package.json'); if(!m.description||!m.keywords) process.exit(1);" || exit 1; done</automated>
  </verify>
  <acceptance_criteria>
    - `npm/bin/voss.js` exists, starts with `#!/usr/bin/env node`, contains the strict pragma, the spawnSync call with `stdio: 'inherit'`, `shell: false`, and the literal arg list `['-m', 'voss.cli', ...]`.
    - Contains both `python.exe` and `bin/python3` branches.
    - Contains SIGINT handling (string literal `'SIGINT'`).
    - File length is under 120 lines (Biome shim is ~50 LOC; ours is ~70 with platform table).
    - Executable bit is set on the file (mode &amp; 0o111).
    - All 5 platform package.json files gain `description` and `keywords` fields without losing their `os`/`cpu`/`files`/`name`/`version` from M6-01.
  </acceptance_criteria>
  <done>The shim is implemented and statically passes structural checks. Behavioral verification against a real PBS extract is deferred to M6-05's pytest smoke test. The shim file is ready to ship in the `@voss/cli` npm package.</done>
</task>

<task type="auto">
  <name>Task 2: Lightweight unit test for shim's pure-logic branches</name>
  <files>tests/packaging/test_npm_shim_logic.py</files>
  <read_first>
    - npm/bin/voss.js (just authored in Task 1)
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §6 (signal exit-code mapping)
    - tests/packaging/test_wheel_install.py (style reference — same dir convention)
  </read_first>
  <action>
    Create `tests/packaging/test_npm_shim_logic.py` — a fast (non-slow) pytest module that exercises the shim's error-message branches without needing a real platform subpackage. The tests invoke `node npm/bin/voss.js` as a subprocess on the developer/CI host:

    - `test_shim_reports_unsupported_platform_or_missing_package`: Run `node npm/bin/voss.js --help` directly with no subpackage installed. Outcome depends on the host: on a *supported* platform (e.g. macOS arm64 in a fresh clone) the shim tries `require.resolve('@voss/cli-darwin-arm64/package.json')` which fails because the subpackage is not in `node_modules` — the shim should exit 1 with stderr containing the string `not installed` and the package name `@voss/cli-`. On an *unsupported* platform/arch (synthetically reproduced by setting env var to override `process.platform` — not portable; skip this branch and rely on the inverse: assert that one of the two error messages was emitted). Concretely: assert `result.returncode == 1` and `('not installed' in stderr) or ('unsupported platform' in stderr)`.
    - `test_shim_has_shebang_and_strict_mode`: Open the file, assert first line starts with `#!/usr/bin/env node` and `'use strict'` appears within the first 5 lines.
    - `test_shim_branches_on_windows_platform`: Open the file, assert both literal substrings `python.exe` AND `bin/python3` appear (catches accidental Windows-only or Unix-only paths).
    - `test_shim_invokes_voss_cli_module_form`: Open the file, assert the literal substring `voss.cli` appears in a spawn-args context (regex match for `'-m'.{0,40}'voss\\.cli'` allowing whitespace).
    - `test_shim_maps_sigint_to_130`: Open the file, assert the string `130` appears OR `128 + signalNums` appears with `SIGINT: 2`. (Static check; a real signal smoke test belongs in M6-05.)

    Use `from tests.packaging.test_entrypoint import _repo_root` for path resolution (PATTERNS.md shared pattern). Skip tests if `which node` returns non-zero. Do NOT mark these `@pytest.mark.slow` — they are file reads + one fast subprocess, well under 1s. The slow integration smoke is M6-05's job.
  </action>
  <verify>
    <automated>command -v node &amp;&amp; pytest -q tests/packaging/test_npm_shim_logic.py 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `tests/packaging/test_npm_shim_logic.py` exists with 5 test functions covering the unsupported-platform branch, shebang+strict, Win/Unix branching, voss.cli module form, and SIGINT→130 mapping.
    - All 5 tests pass on the developer/CI host (assuming node is installed; otherwise the tests skip).
    - The test module is NOT marked `@pytest.mark.slow` (it is fast — file reads + one subprocess invocation).
    - The test module imports `_repo_root` from `tests.packaging.test_entrypoint` (matches PATTERNS.md shared pattern).
  </acceptance_criteria>
  <done>The shim's static guarantees (shebang, strict mode, both OS paths present, module-form spawn, SIGINT mapping) are pinned by a fast test. Drift in any of these breaks the test and signals NPM-03 regression before it reaches CI smoke.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user shell → npm/bin/voss.js | User argv crosses into the shim; the shim does not interpret it, forwards to Python verbatim. |
| npm/bin/voss.js → vendored python interpreter | Spawns a child process; environment is inherited entirely. |
| optionalDependencies install graph | npm resolves which `@voss/cli-<triple>` subpackage is present; shim trusts whichever is on disk. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M6-02-01 | Tampering | argv injection into spawned python | mitigate | `shell: false` in spawnSync — Node spawns the binary directly without shell interpretation. No string concatenation of argv. RESEARCH §6 confirms this is the Biome-pattern stance. |
| T-M6-02-02 | Information Disclosure | env leaks to child python | accept | `env: process.env` passes the full environment by design — voss needs `ANTHROPIC_API_KEY` etc. v0.1 trusts the child. Filtering env would break provider auth (M1 contract). |
| T-M6-02-03 | Spoofing | A malicious package named `@voss/cli-*` slipped into node_modules | accept | npm scope ownership of `@voss` (claimed in M6-01) is the trust root. If the user manually `npm install`s a malicious lookalike (`@voss-cli/...` or `voss-cli-darwin-arm64`), the shim only ever uses names from its hardcoded PLATFORMS table — typosquats outside that table are never resolved. |
| T-M6-02-04 | Denial of Service | Hung child process from misbehaving voss subcommand | accept | The shim does not impose a timeout — `voss do "long task"` legitimately runs long. SIGINT forwarding (T-M6-02-01 mitigation chain) gives the user the kill control. |
| T-M6-02-05 | Tampering | Path traversal via require.resolve result | mitigate | `require.resolve(pkg + '/package.json')` resolves only to a real on-disk package directory; `path.join` on the result is safe. The pkg name comes from a hardcoded table, not user input. |
</threat_model>

<verification>
- `node npm/bin/voss.js --help` exits 1 with a clear stderr message naming the missing platform package (because no platform subpackage is built yet locally — that's M6-03's job).
- `pytest -q tests/packaging/test_npm_shim_logic.py` passes (5 tests).
- `wc -l npm/bin/voss.js` reports <120 lines.
- `ls -l npm/bin/voss.js` shows executable bit set.
</verification>

<success_criteria>
1. The bin shim is implemented end-to-end per RESEARCH §6 and is fully self-contained (no helpers, no external Node deps).
2. Platform dispatch covers exactly the 5 D-13 triples; unknown pairs exit 1 with a clear message.
3. Signal forwarding maps SIGINT→130 and SIGTERM→143 per Unix convention.
4. Exit code from the spawned python is preserved verbatim.
5. A fast pytest pins the shim's structural invariants so accidental edits in later plans break loudly.
</success_criteria>

<output>
After completion, create `.planning/phases/M6-npm-wrapper/M6-02-SUMMARY.md` recording: the final shim's line count, the 5 platform JSON amendments, the pytest module's test names + pass status, and any deviations (e.g. extra signals handled beyond SIGINT/SIGTERM).
</output>
