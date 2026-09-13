---
phase: A4-voss-app-layout-presets
plan: 03
type: execute
wave: 2
depends_on: [A4-00]
files_modified:
  - crates/voss-app-core/src/layouts.rs
  - crates/voss-app-core/src/lib.rs
  - apps/voss-app/src-tauri/src/lib.rs
autonomous: true
requirements: [LAY-06, LAY-07]
must_haves:
  truths:
    - "Rust owns .voss/layouts file I/O"
    - "Layout schema is versioned and wraps GridState"
    - "Path traversal and unsupported/corrupt layout files fail closed"
  artifacts:
    - path: "crates/voss-app-core/src/layouts.rs"
      provides: "LayoutFile schema and save/load helpers"
      contains: "version"
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "Tauri commands for save/load/default layout"
      contains: "save_layout"
---

<objective>
Add the Rust/Tauri layout persistence surface for `.voss/layouts/<name>.json`, with versioned schema, lazy write directory creation, and fail-safe reads.
</objective>

<context>
@.planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md
@.planning/phases/A4-voss-app-layout-presets/A4-RESEARCH.md
@crates/voss-app-core/src/grid.rs
@apps/voss-app/src-tauri/src/lib.rs
</context>

<threat_model>
T-A4-03 Path traversal or unsafe file write. Mitigation: validate layout names; reject separators, `..`, empty names, and suffix confusion. T-A4-04 startup crash on corrupt default layout. Mitigation: return typed no-op/error and log; never panic.
</threat_model>

<tasks>
<task type="tdd">
  <name>Task 1: Add versioned LayoutFile schema and path validation</name>
  <files>crates/voss-app-core/src/layouts.rs, crates/voss-app-core/src/lib.rs</files>
  <read_first>
    - crates/voss-app-core/src/grid.rs — serde-compatible `GridState`
    - crates/voss-app-core/src/lib.rs — module/export pattern
    - .planning/phases/A4-voss-app-layout-presets/A4-CONTEXT.md — D-07/D-09 schema requirements
    - .planning/phases/A4-voss-app-layout-presets/A4-RESEARCH.md — path validation and wrapper guidance
  </read_first>
  <action>
    Add `crates/voss-app-core/src/layouts.rs` defining `LayoutFile { version: u32, active_preset: Option<String>, grid: GridState }` or an equivalent versioned wrapper around `GridState`; current version must be integer `1`. Add name validation returning `Result<(), LayoutError>` that accepts simple names like `default` and `build-watch`, resolves them to `<workspace>/.voss/layouts/<name>.json`, and rejects empty names, `/`, `\\`, `..`, absolute paths, and names ending in `.json` if that would create suffix ambiguity. Export the module from `lib.rs`. Add Rust tests for serde round-trip, version field, accepted names, rejected traversal, and `default` path resolution.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core layouts -- --nocapture && grep -q 'pub struct LayoutFile' crates/voss-app-core/src/layouts.rs && grep -q 'version' crates/voss-app-core/src/layouts.rs && grep -q 'validate_layout_name' crates/voss-app-core/src/layouts.rs && echo LAYOUT_SCHEMA_OK</automated>
  </verify>
  <acceptance_criteria>
    - `LayoutFile` serializes/deserializes with integer `version: 1`.
    - Path validation rejects traversal and separator cases.
    - `cargo test -p voss-app-core layouts` exits 0.
    - `LAYOUT_SCHEMA_OK` prints.
  </acceptance_criteria>
  <done>Versioned layout schema and safe path resolution exist.</done>
</task>

<task type="tdd">
  <name>Task 2: Add Rust save/load/default commands and app registration</name>
  <files>crates/voss-app-core/src/layouts.rs, apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs — current app-level command wrapper pattern
    - crates/voss-app-core/src/layouts.rs — schema/path helpers from Task 1
    - .planning/phases/A4-voss-app-layout-presets/A4-UI-SPEC.md — exact save/load error copy
  </read_first>
  <action>
    Implement Rust functions/commands for `save_layout(workspace_path, name, layout)`, `load_layout(workspace_path, name)`, `list_layouts(workspace_path)`, and `load_default_layout(workspace_path)` or equivalent app-level Tauri command names. Save must lazily create `.voss/layouts` only on write and pretty-write the JSON. Load must not create directories. Missing default returns `Ok(None)`/no-op. Corrupt JSON or unsupported version returns a non-panic error string compatible with UI-SPEC copy (`layout ignored: invalid file`, `layout ignored: unsupported version`). Register the commands in `apps/voss-app/src-tauri/src/lib.rs` alongside existing commands. Add Rust tests using temp dirs for lazy creation, save/load round-trip, list order, missing default, corrupt default, unsupported version, and traversal rejection.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core layouts -- --nocapture && grep -q 'save_layout' apps/voss-app/src-tauri/src/lib.rs && grep -q 'load_layout' apps/voss-app/src-tauri/src/lib.rs && grep -q 'load_default_layout' apps/voss-app/src-tauri/src/lib.rs && echo LAYOUT_IO_OK</automated>
  </verify>
  <acceptance_criteria>
    - Save creates `.voss/layouts` only when saving.
    - Load/list/default commands never create `.voss`.
    - Corrupt and unsupported layout files fail closed without panic.
    - Tauri app registers save/load/list/default layout commands.
    - `LAYOUT_IO_OK` prints.
  </acceptance_criteria>
  <done>Rust layout persistence commands are implemented and registered.</done>
</task>
</tasks>

<verification>
Run `cargo test -p voss-app-core layouts -- --nocapture` and a build after app command registration.
</verification>

<success_criteria>
- Layout files use a versioned JSON schema.
- `.voss/` is lazy-created only on save.
- Invalid paths and corrupt/unsupported layouts fail safely.
</success_criteria>

