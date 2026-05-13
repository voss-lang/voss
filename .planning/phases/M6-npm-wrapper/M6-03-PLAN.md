---
phase: M6-npm-wrapper
plan: 03
type: execute
wave: 2
depends_on: ["M6-01"]
files_modified:
  - npm/scripts/prune_pbs.py            # CREATE
  - npm/scripts/build_platform.py       # CREATE
  - npm/scripts/bump_version.py         # CREATE
  - npm/scripts/pbs_manifest.json       # CREATE
  - tests/packaging/test_npm_scripts.py # CREATE
autonomous: false
requirements: [NPM-02]
must_haves:
  truths:
    - "`python3 npm/scripts/bump_version.py` rewrites `npm/package.json` and all 5 `npm/platforms/<triple>/package.json` files so their `version` matches `pyproject.toml [project] version`"
    - "`python3 npm/scripts/bump_version.py main` updates only `npm/package.json`"
    - "`python3 npm/scripts/bump_version.py <triple>` updates only that platform's package.json"
    - "`python3 npm/scripts/prune_pbs.py <pbs-extract-dir>` removes the RESEARCH §4 targets on Unix and the equivalent set on Windows, idempotently"
    - "`python3 npm/scripts/build_platform.py <triple> --out npm/platforms/<triple>/python` orchestrates: download PBS tarball, verify sha256 against pbs_manifest.json, extract, prune, pip install voss wheel into vendored site-packages, then print and gate on the site-packages size"
    - "build_platform.py prints a SITE_PACKAGES_SIZE_MB=<N> line to stdout after install; if N > 300 it exits non-zero with a SIZE_BUDGET_EXCEEDED message so CI fails loud (RESEARCH §5 Risk 2)"
    - "pbs_manifest.json pins the PBS release tag 20260510, python version 3.12.13, and per-triple sha256 slots that build_platform.py verifies before extracting"
  artifacts:
    - path: "npm/scripts/bump_version.py"
      provides: "Version-sync from pyproject.toml to npm package.json files (D-10)"
      contains: "tomllib"
    - path: "npm/scripts/prune_pbs.py"
      provides: "Idempotent prune of vendored Python tree per D-07 + RESEARCH §4"
      contains: "idlelib"
    - path: "npm/scripts/build_platform.py"
      provides: "PBS download + sha verify + extract + prune + wheel install orchestration"
      contains: "pbs_manifest"
    - path: "npm/scripts/pbs_manifest.json"
      provides: "Pinned PBS release tag + per-triple sha256 record"
      contains: "20260510"
    - path: "tests/packaging/test_npm_scripts.py"
      provides: "Fast unit tests for bump_version + prune_pbs (no PBS download)"
  key_links:
    - from: "npm/scripts/bump_version.py"
      to: "pyproject.toml"
      via: "tomllib.load + project.version"
      pattern: "tomllib\\.load"
    - from: "npm/scripts/bump_version.py"
      to: "npm/package.json + npm/platforms/*/package.json"
      via: "json read-modify-write"
      pattern: "json\\.dumps"
    - from: "npm/scripts/build_platform.py"
      to: "npm/scripts/prune_pbs.py"
      via: "subprocess.run([sys.executable, prune_pbs.py, ...])"
      pattern: "prune_pbs"
    - from: "npm/scripts/build_platform.py"
      to: "npm/scripts/pbs_manifest.json"
      via: "json.load + hashlib.sha256 verify"
      pattern: "hashlib\\.sha256"
---

<objective>
M6-03 is the build-machinery plan. It creates three Python scripts the M6-04 release workflow will call once per platform: prune_pbs.py (trims the vendored Python per D-07 / RESEARCH §4), build_platform.py (orchestrates PBS download + sha verify + extract + prune + wheel install), and bump_version.py (D-10 version-sync from pyproject.toml). It also creates pbs_manifest.json which pins the PBS release tag + per-triple sha256 hashes — the supply-chain anchor for the npm package.

Purpose: NPM-02 demands "vendors a pinned Python interpreter + the v0.1 voss wheel". These three scripts are the mechanism. They run on each per-platform CI runner in M6-04 to produce the npm/platforms/<triple>/python/ tree that `npm publish` ships. This plan also resolves RESEARCH §14 Open Question 1 + Risk 2: by running build_platform.py once locally on the developer's host platform during this plan and reading the SITE_PACKAGES_SIZE_MB number, the user gets a hard answer to "does sentence-transformers pull PyTorch?" BEFORE committing to the 5-way fan-out publish in M6-04.

Output: Three executable Python scripts + one JSON manifest under npm/scripts/, a fast pytest module that exercises the pure-logic branches of bump_version + prune_pbs without needing a real PBS download, and a [BLOCKING] human-verify checkpoint that gates M6-04 on the actual measured site-packages size.
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
@pyproject.toml
@tests/packaging/test_wheel_install.py
@voss/cli.py

<interfaces>
Behavioral contracts these scripts must honor. bump_version.py and the build pipeline have partial analogs in the codebase (PATTERNS.md). The relevant excerpts:

From pyproject.toml line 7:
  version = "0.1.0"   (single source of truth, D-10)

bump_version.py CLI surface (RESEARCH §8):
  python3 npm/scripts/bump_version.py             # update all 6 package.jsons
  python3 npm/scripts/bump_version.py main        # update npm/package.json only
  python3 npm/scripts/bump_version.py darwin-arm64   # update one platform

prune_pbs.py CLI surface:
  python3 npm/scripts/prune_pbs.py <dir-containing-python/>
  Auto-detects shape: if `python/python.exe` exists -> Windows targets;
  elif `python/bin/python3` exists -> Unix targets; else exit 2.

Unix prune targets (RESEARCH §4):
  PRUNE_DIRS: include, lib/python3.12/idlelib, lib/python3.12/tkinter,
              lib/python3.12/lib2to3, lib/python3.12/ensurepip,
              lib/python3.12/turtledemo, share
  PRUNE_GLOBS (under lib/): itcl*, tcl*, tk*, thread*
  PRUNE_BINS (under bin/): 2to3, 2to3-3.12, idle3, idle3.12,
                           python3-config, python3.12-config

Windows prune targets (RESEARCH §4):
  PRUNE_DIRS: include, Lib/idlelib, Lib/tkinter, Lib/lib2to3,
              Lib/turtledemo, tcl
  PRUNE_FILES: pythonw.exe

build_platform.py CLI surface:
  python3 npm/scripts/build_platform.py <triple> --out <dir> [--wheel <path>] [--keep-tarball]
  triple in {darwin-arm64, darwin-x64, linux-x64, linux-arm64, win32-x64}
  --out: destination for the prepared python/ directory
         (M6-04 sets this to npm/platforms/<triple>/python)
  --wheel: optional pre-built wheel path; absent -> runs `python -m build --wheel`
  --keep-tarball: keep the PBS download for debugging
  Exit 0 on success; exit 1 with stderr SIZE_BUDGET_EXCEEDED if site-packages > 300 MB.

PBS download URL (RESEARCH §3):
  https://github.com/astral-sh/python-build-standalone/releases/download/20260510/
    cpython-3.12.13+20260510-<pbs-triple>-install_only_stripped.tar.gz
  Mapping:
    darwin-arm64  -> aarch64-apple-darwin
    darwin-x64    -> x86_64-apple-darwin
    linux-x64     -> x86_64-unknown-linux-gnu
    linux-arm64   -> aarch64-unknown-linux-gnu
    win32-x64     -> x86_64-pc-windows-msvc

Python entrypoint inside vendored interpreter:
  Unix:    <out>/bin/python3
  Windows: <out>/python.exe

Reused patterns from tests/packaging/test_wheel_install.py: `_repo_root`,
`subprocess.run(..., check=True, timeout=...)` shape, Windows path branch idiom.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: bump_version.py + prune_pbs.py + pbs_manifest.json + unit tests</name>
  <files>npm/scripts/bump_version.py, npm/scripts/prune_pbs.py, npm/scripts/pbs_manifest.json, tests/packaging/test_npm_scripts.py</files>
  <read_first>
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §3 (PBS releases + URLs), §4 (prune layout), §8 (bump_version logic)
    - .planning/phases/M6-npm-wrapper/M6-PATTERNS.md "bump_version.py", "prune_pbs.py"
    - voss/cli.py top 90 lines (the `_write_text_atomic` idiom — pattern reference; bump_version does NOT need atomic write)
    - pyproject.toml [project] block (confirm version key location)
    - scripts/dump_python_plan_schema.py (analog Python script header style)
  </read_first>
  <behavior>
    bump_version.py:
    - Test 1: with `version = "0.2.3"` in a fake pyproject.toml + 6 placeholder package.jsons in a tmp tree, calling bump_version.py (no args) sets all 6 to 0.2.3 and updates optionalDependencies values in the main package.json.
    - Test 2: bump_version.py main only touches npm/package.json.
    - Test 3: bump_version.py darwin-arm64 only touches npm/platforms/darwin-arm64/package.json.
    - Test 4: each rewritten file uses 2-space indent and trailing newline (matches M6-01 placeholder format).
    - Test 5: invalid triple name exits non-zero with a stderr message.

    prune_pbs.py:
    - Test 6: given a synthetic Unix tree (python/lib/python3.12/idlelib/__init__.py, python/lib/python3.12/tkinter/Tkinter.py, python/include/Python.h, python/lib/python3.12/site-packages/.placeholder, python/bin/python3 stub), prune removes the first three but preserves site-packages and the bin/python3 stub.
    - Test 7: running prune twice is idempotent (second run exits 0, removes nothing more).
    - Test 8: fabricated Windows-shaped tree (python/python.exe, python/Lib/idlelib/, python/Lib/site-packages/, python/tcl/, python/pythonw.exe) on a non-Windows host: prune still removes the Win prune targets (auto-detected by the python.exe sentinel file).
  </behavior>
  <action>
    Write four files.

    bump_version.py (~50 LOC). Header per the PATTERNS.md "Python script header" shared pattern: `from __future__ import annotations`, then `import sys, json, tomllib`, then `from pathlib import Path`. Define `ROOT = Path(__file__).resolve().parents[2]`, `PYPROJECT = ROOT / "pyproject.toml"`, `NPM_DIR = ROOT / "npm"`, `PLATFORMS = ["darwin-arm64", "darwin-x64", "linux-x64", "linux-arm64", "win32-x64"]`. Read the version: open pyproject.toml in binary mode, `tomllib.load(f)["project"]["version"]`. Implement `update_json(path, version)` per RESEARCH §8: read with `json.loads(path.read_text())`, set `data["version"] = version`, also rewrite each key inside `data.get("optionalDependencies", {})` to the new version, then `path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")`. CLI: parse `sys.argv[1]` (default "all"); validate against `{"all", "main", *PLATFORMS}`; on invalid token, print to stderr and exit 2. Apply updates per the surface in the `<interfaces>` block. Print `Updated <path> -> <version>` for each touched file. Do NOT use the atomic-write idiom from voss/cli.py — bump_version is not concurrent; plain write_text matches RESEARCH §8. Make the file executable (mode 0o755).

    prune_pbs.py (~80 LOC). Same header pattern. Imports: `from __future__ import annotations`, then `import shutil, sys, argparse`, then `from pathlib import Path`. Define UNIX_PRUNE_DIRS, UNIX_PRUNE_GLOBS, UNIX_PRUNE_BINS, WIN_PRUNE_DIRS, WIN_PRUNE_FILES exactly per the lists in the `<interfaces>` block. Implement `prune_path(p) -> bool` that returns True if a removal happened. Use `shutil.rmtree(p, ignore_errors=False)` for directories — guard with `if p.is_dir()`. For files / symlinks, `p.unlink(missing_ok=True)` (works for both regular files and symlinks). Auto-detect platform shape: read the positional arg as `root` (the directory containing `python/`); if `(root / "python" / "python.exe").exists()` -> Windows targets; elif `(root / "python" / "bin" / "python3").exists()` -> Unix targets; else write to stderr and exit 2. Iterate the targets; for each, log `Pruned: <relpath>` if removed, else `Skipped (absent): <relpath>`. Accept `--dry-run` flag that logs without removing. Exit 0 even if some targets are absent (PBS layouts evolve; missing prune targets are OK and explicitly expected to be tolerated per RESEARCH §4 "ensurepip safe to prune" comment). Make file executable.

    pbs_manifest.json. Shape:
    {
      "_README": "Edit sha256 values from PENDING to actual digests as build_platform.py prints them. Each triple's sha is pinned the first time that triple's runner builds in CI; flip from PENDING to a real hex string and commit.",
      "pbs_release": "20260510",
      "python_version": "3.12.13",
      "source": "https://github.com/astral-sh/python-build-standalone",
      "url_template": "https://github.com/astral-sh/python-build-standalone/releases/download/{pbs_release}/cpython-{python_version}+{pbs_release}-{pbs_triple}-install_only_stripped.tar.gz",
      "triples": {
        "darwin-arm64": {"pbs_triple": "aarch64-apple-darwin", "sha256": "PENDING"},
        "darwin-x64":   {"pbs_triple": "x86_64-apple-darwin",  "sha256": "PENDING"},
        "linux-x64":    {"pbs_triple": "x86_64-unknown-linux-gnu", "sha256": "PENDING"},
        "linux-arm64":  {"pbs_triple": "aarch64-unknown-linux-gnu","sha256": "PENDING"},
        "win32-x64":    {"pbs_triple": "x86_64-pc-windows-msvc",   "sha256": "PENDING"}
      }
    }
    Write with `json.dumps(data, indent=2) + "\n"`. Task 3 will replace the host-triple's PENDING with the real sha256.

    tests/packaging/test_npm_scripts.py. Implement Tests 1..8 above. Use `tmp_path` fixtures, write fake pyproject.toml + package.json files into the tmp tree, invoke the scripts via `subprocess.run([sys.executable, str(script), ...], check=True, capture_output=True, text=True, timeout=30)`. Import `_repo_root` from `tests.packaging.test_entrypoint`. Do NOT mark these `@pytest.mark.slow`; the whole module should finish in well under 5 seconds.
  </action>
  <verify>
    <automated>chmod +x npm/scripts/bump_version.py npm/scripts/prune_pbs.py; python3 -c "import json; m=json.load(open('npm/scripts/pbs_manifest.json')); assert m['pbs_release']=='20260510' and m['python_version']=='3.12.13' and set(m['triples'].keys())=={'darwin-arm64','darwin-x64','linux-x64','linux-arm64','win32-x64'}, m" &amp;&amp; pytest -q tests/packaging/test_npm_scripts.py</automated>
  </verify>
  <acceptance_criteria>
    - npm/scripts/bump_version.py is executable, parses pyproject.toml via tomllib, updates 1 or 6 package.json files based on the CLI arg, and rewrites optionalDependencies values in the main package.json.
    - npm/scripts/prune_pbs.py is executable, auto-detects Unix vs Windows shape, removes RESEARCH §4 targets, is idempotent.
    - npm/scripts/pbs_manifest.json exists with pbs_release 20260510, python_version 3.12.13, all 5 triples, sha256 slots initially "PENDING", url_template present.
    - tests/packaging/test_npm_scripts.py exists with 8 tests covering Test 1..Test 8; all pass on the developer host.
  </acceptance_criteria>
  <done>Three scripts + one manifest + one test module exist. Version-sync and prune logic are pinned by fast tests. PBS download / verify is unimplemented in this task — it lands in Task 2.</done>
</task>

<task type="auto">
  <name>Task 2: build_platform.py orchestration script</name>
  <files>npm/scripts/build_platform.py</files>
  <read_first>
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §3 (PBS download URLs), §4 (post-extract layout), §5 (wheel install mechanics + Risk 2 size budget), §10 (file permissions)
    - tests/packaging/test_wheel_install.py (subprocess + timeout pattern reference)
    - npm/scripts/pbs_manifest.json (just authored in Task 1)
    - npm/scripts/prune_pbs.py (just authored in Task 1)
  </read_first>
  <action>
    Write npm/scripts/build_platform.py (~150 LOC). Header per the PATTERNS.md shared pattern. Imports: `from __future__ import annotations`, then `import argparse, hashlib, json, os, shutil, subprocess, sys, tarfile, tempfile, urllib.request`, then `from pathlib import Path`. Module constants: `ROOT = Path(__file__).resolve().parents[2]`, `MANIFEST = ROOT / "npm" / "scripts" / "pbs_manifest.json"`, `PRUNE_SCRIPT = ROOT / "npm" / "scripts" / "prune_pbs.py"`, `SIZE_BUDGET_MB = 300` (RESEARCH §5 Risk 2 threshold). A 5-line module docstring stating purpose plus the SIZE_BUDGET_MB rationale.

    Implement nine functions, names exactly as listed (the verify step AST-greps for them):

    1. load_manifest() -> dict. Read MANIFEST and json-decode.
    2. download_pbs(triple, manifest, dest) -> Path. Format the URL via manifest["url_template"].format(pbs_release=..., python_version=..., pbs_triple=manifest["triples"][triple]["pbs_triple"]). Stream with urllib.request.urlopen into `dest / "pbs.tar.gz"` (chunk size 64K). Print `Downloaded <url> -> <bytes> bytes`.
    3. verify_sha256(tarball, expected) -> str. Compute sha256 in 64K chunks. If expected == "PENDING": print `SHA256(<filename>)=<digest>` and a hint `Update pbs_manifest.json for <triple> with this digest, then commit.`; do NOT fail (this lets the first build on each triple capture the hash). If expected is a hex string: compare. On mismatch, write to stderr and sys.exit(2). Return the computed digest.
    4. extract_pbs(tarball, dest) -> Path. `with tarfile.open(tarball, 'r:gz') as t: t.extractall(dest)`. PBS tarballs contain a top-level `python/` directory; return `dest / "python"`. Confirm the expected interpreter exists post-extract (Unix: `python/bin/python3`; Windows: `python/python.exe`); else stderr-error and exit 2.
    5. run_prune(extract_root) -> None. `subprocess.run([sys.executable, str(PRUNE_SCRIPT), str(extract_root.parent)], check=True, timeout=120)`. (prune_pbs.py takes the directory ABOVE `python/`.)
    6. install_wheel(extract_root, wheel) -> None. Compute python_bin per branch (Windows -> `extract_root/python.exe`; Unix -> `extract_root/bin/python3`). On Unix, `os.chmod(python_bin, 0o755)` first (PBS preserves the bit but be safe). `subprocess.run([str(python_bin), "-m", "pip", "install", "--no-cache-dir", str(wheel)], check=True, timeout=900)`. Do NOT pass --target or --prefix (RESEARCH §5 explicit).
    7. measure_site_packages(extract_root) -> int. Resolve the site-packages dir per platform (Unix: `extract_root/lib/python3.12/site-packages`; Windows: `extract_root/Lib/site-packages`). Walk it with Path.rglob("*"); sum st_size of regular files; do not follow symlinks. Return total bytes.
    8. ensure_wheel(wheel_arg) -> Path. If wheel_arg is a Path that exists, return it. Else: `subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(ROOT / "dist"), str(ROOT)], check=True, timeout=600)`, then glob `ROOT / "dist" / "voss-*.whl"`, assert exactly one match, return it. (Same call shape as tests/packaging/test_wheel_install.py:_build_wheel.)
    9. main() -> int. Argparse: positional `triple` (choices = 5 triples), `--out` (required Path), `--wheel` (optional Path), `--keep-tarball` (flag). Orchestration: manifest = load_manifest(); wheel = ensure_wheel(args.wheel); within a tempfile.TemporaryDirectory as tmp: tarball = download_pbs(...); verify_sha256(tarball, manifest["triples"][triple]["sha256"]); extract_root = extract_pbs(...); run_prune(extract_root); install_wheel(extract_root, wheel); size_bytes = measure_site_packages(extract_root); size_mb = size_bytes // (1024*1024). Move the extract_root to args.out (rmtree args.out first if it exists). Print `SITE_PACKAGES_SIZE_MB=<size_mb>` on its own line (CI grep). If size_mb > SIZE_BUDGET_MB: write `SIZE_BUDGET_EXCEEDED budget=<SIZE_BUDGET_MB> actual=<size_mb>` to stderr and return 1. Else return 0.

    Make the file executable. The 9-function structure is verified by AST grep in the verify block.

    Note: end-to-end exercise against ONE triple (the developer host) happens in Task 3. The other 4 triples are exercised by M6-04 CI; this plan does not run them.
  </action>
  <verify>
    <automated>chmod +x npm/scripts/build_platform.py &amp;&amp; python3 npm/scripts/build_platform.py --help 2>&amp;1 | grep -E "triple|--out|--wheel" &amp;&amp; python3 -c "import ast; t=ast.parse(open('npm/scripts/build_platform.py').read()); fns={n.name for n in ast.walk(t) if isinstance(n, ast.FunctionDef)}; need={'load_manifest','download_pbs','verify_sha256','extract_pbs','run_prune','install_wheel','measure_site_packages','ensure_wheel','main'}; missing=need-fns; assert not missing, f'missing: {missing}'; src=open('npm/scripts/build_platform.py').read(); assert 'SITE_PACKAGES_SIZE_MB=' in src and 'SIZE_BUDGET_EXCEEDED' in src and 'SIZE_BUDGET_MB = 300' in src"</automated>
  </verify>
  <acceptance_criteria>
    - npm/scripts/build_platform.py is executable.
    - `--help` lists triple, --out, --wheel, --keep-tarball.
    - AST inspection finds all 9 expected function names.
    - Module-level constant `SIZE_BUDGET_MB = 300` is present.
    - Literal strings `SITE_PACKAGES_SIZE_MB=` and `SIZE_BUDGET_EXCEEDED` are present (CI greps for these).
    - Imports include urllib.request, tarfile, hashlib, subprocess.
  </acceptance_criteria>
  <done>The orchestration script exists with all helpers and CLI. End-to-end exercise on the host platform happens in Task 3.</done>
</task>

<task type="auto">
  <name>Task 3: End-to-end build_platform.py run on host platform + manifest sha update</name>
  <files>npm/scripts/pbs_manifest.json, .planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt</files>
  <read_first>
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §5 (Risk 2 — PyTorch size risk; this task resolves it)
    - npm/scripts/build_platform.py (just authored)
    - npm/scripts/pbs_manifest.json (just authored)
  </read_first>
  <action>
    Detect the developer host's npm-triple: run `python3 -c "import platform; s=platform.system().lower(); m=platform.machine().lower(); print({'darwin':'darwin','linux':'linux'}.get(s,s) + '-' + {'arm64':'arm64','aarch64':'arm64','x86_64':'x64','amd64':'x64'}.get(m,m))"`. Per STATE.md the user is on `darwin` so the most likely answer is `darwin-arm64` (Apple Silicon) or `darwin-x64`. If the detected triple is not one of the 5 supported, surface a `## PLANNING INCONCLUSIVE` and ask the user how to proceed (e.g. they may want to run this task on a CI runner instead).

    Run end-to-end:
    `python3 npm/scripts/build_platform.py <host-triple> --out /tmp/voss-m6-host-build/python 2>&1 | tee .planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt`

    The script will: build the voss wheel (~30-60s), download the PBS tarball (~23MB on macOS, ~32MB on linux-x64), print the computed sha256 (manifest says PENDING for this triple), extract, prune, run pip install of the wheel (~2-5 min — chromadb, onnxruntime, sentence-transformers, etc), then print SITE_PACKAGES_SIZE_MB.

    After the run completes:
    1. Edit npm/scripts/pbs_manifest.json — replace the host-triple's `"sha256": "PENDING"` with the actual digest from the log. Leave the other 4 triples at PENDING (they get filled in by M6-04 CI on each runner's first build, or by a developer manually rerunning build_platform.py on another machine).
    2. Append a `## RESULT` section to M6-03-host-build-log.txt summarizing: detected triple, PBS tarball sha256, SITE_PACKAGES_SIZE_MB number, wall-clock time, any unexpected warnings.
    3. Sanity-check the built python: `/tmp/voss-m6-host-build/python/bin/python3 -c "import voss.cli; print(voss.cli.__file__)"` should exit 0 and print a path inside the vendored site-packages.
    4. Sanity-check the CLI: `/tmp/voss-m6-host-build/python/bin/python3 -m voss.cli --help` should exit 0 and print voss help text.
    5. Clean up /tmp/voss-m6-host-build/ (the artifact is not committed; the log is).
  </action>
  <verify>
    <automated>test -f .planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt &amp;&amp; grep -E "SITE_PACKAGES_SIZE_MB=[0-9]+" .planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt &amp;&amp; grep -E "^## RESULT" .planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt &amp;&amp; python3 -c "import json; m=json.load(open('npm/scripts/pbs_manifest.json')); pending=sum(1 for v in m['triples'].values() if v['sha256']=='PENDING'); assert pending&lt;=4, f'expected at most 4 PENDING after host build, found {pending}'"</automated>
  </verify>
  <acceptance_criteria>
    - .planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt exists and contains the SITE_PACKAGES_SIZE_MB line plus a ## RESULT section.
    - npm/scripts/pbs_manifest.json has the host-triple's sha256 filled in (no longer "PENDING"); the other 4 triples remain "PENDING".
    - The vendored python successfully imports voss.cli and runs `python -m voss.cli --help` with exit 0 (proven in the log).
    - The build_platform.py exit code was 0 (not 1 from SIZE_BUDGET_EXCEEDED). If exit was 1, the [BLOCKING] checkpoint below resolves the disposition.
  </acceptance_criteria>
  <done>build_platform.py is proven end-to-end on at least one platform. The actual site-packages size is measured and recorded. The host triple's PBS sha256 is pinned.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 4: [BLOCKING] Approve site-packages size budget before M6-04 fan-out publish</name>
  <what-built>
    Task 3 produced a measured SITE_PACKAGES_SIZE_MB number written to .planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt. This number is the answer to RESEARCH §14 Open Question 1 (PyTorch transitive size risk) and RESEARCH §5 Risk 2. The build_platform.py script enforces a 300 MB hard cap; below 300 MB the script exited 0, above 300 MB it exited 1.
  </what-built>
  <how-to-verify>
    1. Open .planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt and read the SITE_PACKAGES_SIZE_MB line + the ## RESULT section.
    2. Interpret the result:
       - If SIZE_MB < 200: green. Proceed to M6-04 without changes. The 100 MB headroom is comfortable for npm publish.
       - If 200 <= SIZE_MB <= 300: yellow. Proceed to M6-04 but flag to add an `npm pack --dry-run` size check inside the M6-04 workflow before each platform publishes.
       - If SIZE_MB > 300: red. build_platform.py already exited 1. Do NOT proceed to M6-04 as-is. Options:
         (a) Pin sentence-transformers without the torch extra in pyproject.toml (run a quick `pip show sentence-transformers` + `pip show torch` to confirm torch was the bloat source); revise the wheel; re-run Task 3.
         (b) Carve sentence-transformers / chromadb behind an optional install path (`voss[search]` extra) so the default npm package excludes them; this is a larger scope shift.
         (c) Raise SIZE_BUDGET_MB in build_platform.py to a higher value (e.g. 500) if 300-500 MB is acceptable for npm; document the rationale in M6-03-host-build-log.txt.
    3. Decide which colour/option applies and respond. The decision determines whether M6-04 starts as-planned or whether a follow-up (M6-03.5) is needed to revise the wheel deps first.
  </how-to-verify>
  <acceptance_criteria>
    - User has read the SITE_PACKAGES_SIZE_MB number.
    - User explicitly approves one of: "green, proceed M6-04", "yellow, proceed M6-04 with npm pack dry-run check added", "red, hold M6-04 and revise wheel deps in option (a/b/c)".
    - The decision is recorded in .planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt under a `## DECISION` heading appended by the executor.
  </acceptance_criteria>
  <resume-signal>Reply "green", "yellow", or "red: option a|b|c" plus any required follow-up notes.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| GitHub releases (PBS tarball) -> local CI runner | Third-party binary download; tampering risk on the path. |
| PyPI (transitive wheel deps) -> vendored Python | pip install pulls C-extension wheels from PyPI on each runner. |
| Developer machine -> pbs_manifest.json | Manifest stores supply-chain anchors (sha256); editing it is privileged. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M6-03-01 | Tampering | PBS tarball replaced upstream after first sha pin | mitigate | verify_sha256 in build_platform.py compares against pbs_manifest.json. Once a triple's sha is pinned (not PENDING), any mismatch exits 2. First build per triple captures the sha and prints it for manual review + commit. |
| T-M6-03-02 | Tampering | pyproject.toml version manipulated between bump and publish | mitigate | M6-04 release workflow re-runs bump_version.py at CI time AND has a pre-publish verify step (RESEARCH §8) that fails if npm/package.json version != pyproject.toml version. |
| T-M6-03-03 | Information Disclosure | PBS download URL or sha logged to stdout exposes internal infrastructure | accept | URLs and digests are public; no secret material. Logging aids audit. |
| T-M6-03-04 | Denial of Service | A malicious sentence-transformers update inflates site-packages above any sane budget | mitigate | SIZE_BUDGET_MB = 300 hard cap in build_platform.py; CI fails loud rather than publishing an unusable 1GB package. Task 4 checkpoint is the human gate. |
| T-M6-03-05 | Tampering | prune_pbs.py removes a load-bearing stdlib file | mitigate | Task 1 Test 6 + Test 8 pin the prune target set; Task 3 confirms `python -m voss.cli --help` exits 0 against the pruned tree (proves no stdlib essential to voss was removed). |
| T-M6-03-06 | Tampering | Wheel substitution between ensure_wheel and install_wheel | accept | Both run in the same process within a TemporaryDirectory; no cross-process boundary; no PyPI dependency (wheel is built locally from the same git checkout). |
</threat_model>

<verification>
- All 4 scripts/manifests exist under npm/scripts/ with executable bits where applicable.
- pytest -q tests/packaging/test_npm_scripts.py passes (8 tests).
- npm/scripts/build_platform.py --help works and exposes the 4 expected flags.
- M6-03-host-build-log.txt exists with SITE_PACKAGES_SIZE_MB measured.
- pbs_manifest.json has the host triple's sha256 filled in.
- Task 4 checkpoint has a recorded user decision (green/yellow/red).
</verification>

<success_criteria>
1. NPM-02's build pipeline is implementable: prune_pbs.py + build_platform.py + bump_version.py + pbs_manifest.json all exist and are exercised.
2. The PyTorch size risk (RESEARCH §14 Q1 / §5 Risk 2) has a measured answer, not an assumption.
3. The version-sync mechanism (D-10) is mechanically pinned by Test 1..Test 4.
4. The supply-chain mitigation (sha256 verify) is wired into build_platform.py and exercised on at least one triple.
5. M6-04 has explicit go/no-go input from Task 4's checkpoint before fan-out publish.
</success_criteria>

<output>
After completion, create .planning/phases/M6-npm-wrapper/M6-03-SUMMARY.md recording: function names + line counts for each script, the measured SITE_PACKAGES_SIZE_MB, the user's Task 4 decision (green/yellow/red and any follow-up), the host-triple sha256 added to pbs_manifest.json, and the count of remaining PENDING sha256 slots.
</output>
