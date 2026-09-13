---
phase: A12-voss-app-ade-visual-redesign
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/src/themes/bundled/voss-ignite.json
  - apps/voss-app/src/themes/themeCatalog.ts
  - apps/voss-app/src/themes/themeRuntime.ts
  - apps/voss-app/src/index.css
  - apps/voss-app/public/fonts/poppins-500.woff2
  - apps/voss-app/public/fonts/poppins-600.woff2
  - apps/voss-app/src/themes/__tests__/voss-ignite.test.ts
autonomous: true
requirements:
  - ADE-01

must_haves:
  truths:
    - "App renders with warm site palette — no cool blue-grays remain"
    - "Terminal surfaces use warm ANSI palette (orange cursor, warm blacks/whites)"
    - "Poppins display font loads and renders in-app (locally bundled, not Google Fonts)"
    - "Variant B theme is preserved as a fallback option in the theme catalog"
    - "Voss Ignite is the default theme on fresh launch"
  artifacts:
    - path: "apps/voss-app/src/themes/bundled/voss-ignite.json"
      provides: "Voss Ignite theme definition with all 27 REQUIRED_CSS_VARS + new tokens"
      contains: "voss-ignite"
    - path: "apps/voss-app/public/fonts/poppins-500.woff2"
      provides: "Poppins Medium font file for display headings"
    - path: "apps/voss-app/public/fonts/poppins-600.woff2"
      provides: "Poppins SemiBold font file for section headings"
    - path: "apps/voss-app/src/themes/__tests__/voss-ignite.test.ts"
      provides: "Schema conformance test for Ignite theme"
  key_links:
    - from: "apps/voss-app/src/themes/themeCatalog.ts"
      to: "apps/voss-app/src/themes/bundled/voss-ignite.json"
      via: "import + BUNDLED_BY_ID registration"
      pattern: "import vossIgnite"
    - from: "apps/voss-app/src/themes/themeRuntime.ts"
      to: "apps/voss-app/src/themes/themeCatalog.ts"
      via: "getBundledTheme('voss-ignite')"
      pattern: "getBundledTheme.*voss-ignite"
    - from: "apps/voss-app/src/index.css"
      to: "apps/voss-app/public/fonts/"
      via: "@font-face src url"
      pattern: "font-family.*Poppins"
---

<objective>
Create the "Voss Ignite" warm theme as a new bundled theme entry and make it the default. Bundle Poppins font files locally (CSP blocks Google Fonts — RESEARCH Finding 1). Add new CSS tokens for roles, sidebar width, focus-soft, font-display, and titlebar height. Preserve Variant B as a fallback theme.

Purpose: All subsequent A12 plans depend on the warm token palette. Theme is the foundation layer.
Output: voss-ignite.json, @font-face declarations, updated themeCatalog + themeRuntime, schema conformance test.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-CONTEXT.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md

<interfaces>
<!-- Key types and contracts the executor needs. -->

From apps/voss-app/src/themes/schema.ts:
- REQUIRED_CSS_VARS: 27 keys (--bg-0 through --window-opacity-bg)
- Theme type: { id, name, appearance, cssVars, ansi, selection?, cursor?, cursorText? }
- validateTheme(value: unknown): ThemeValidationResult
- contrastRatio(a: string, b: string): number

From apps/voss-app/src/themes/themeCatalog.ts:
- BUNDLED_THEME_IDS: readonly string[] (currently 12 entries)
- BUNDLED_BY_ID: Record<BundledThemeId, Theme>
- getBundledTheme(id: string): Theme | undefined
- resolveThemeCssVars(theme, highContrastEnabled): Record<string, string>

From apps/voss-app/src/themes/themeRuntime.ts:
- DEFAULT_THEME = getBundledTheme('variant-b')! (line 11 — change to 'voss-ignite')
- themeToXtermTheme(theme, highContrast?): ITheme
- applyThemeToRuntime(theme, options?): void
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Voss Ignite theme JSON and bundle Poppins fonts</name>
  <files>
    apps/voss-app/src/themes/bundled/voss-ignite.json,
    apps/voss-app/public/fonts/poppins-500.woff2,
    apps/voss-app/public/fonts/poppins-600.woff2,
    apps/voss-app/src/index.css
  </files>
  <read_first>
    apps/voss-app/src/themes/schema.ts,
    apps/voss-app/src/themes/bundled/variant-b.json,
    apps/voss-app/src/index.css,
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md (Finding 1: CSP font constraint, Code Examples: Theme JSON)
  </read_first>
  <action>
    1. Create directory apps/voss-app/public/fonts/ if it does not exist.

    2. Download Poppins woff2 files from Google Fonts static CDN. Use curl to fetch:
       - Poppins 500 (medium): https://fonts.gstatic.com/s/poppins/v22/pxiByp8kv8JHgFVrLGT9Z1JlFd2JQEl8qw.woff2
       - Poppins 600 (semibold): https://fonts.gstatic.com/s/poppins/v22/pxiByp8kv8JHgFVrLDz8Z1JlFd2JQEl8qw.woff2
       Save to apps/voss-app/public/fonts/poppins-500.woff2 and poppins-600.woff2.
       Verify each file is >10KB (valid woff2). If the exact URLs fail, navigate to https://fonts.google.com/specimen/Poppins and obtain latin subset woff2 for weights 500 and 600.

    3. Create apps/voss-app/src/themes/bundled/voss-ignite.json. The JSON must contain:
       - id: "voss-ignite", name: "Voss Ignite", appearance: "dark"
       - cssVars object with ALL 27 keys from REQUIRED_CSS_VARS (verified against schema.ts):
         --bg-0: #0b0a09, --bg-1: #131110, --bg-2: #1a1714, --bg-3: #221f1b
         --fg-0: #f5f1ea, --fg-1: #c4beb5, --fg-2: #8a847a, --fg-3: #5a554d
         --border: #1d1a16, --border-bright: #2e2924
         --focus: #ff5b1f, --focus-glow: rgba(255,91,31,0.18)
         --accent-green: #5ec26a, --accent-amber: #e8b86c, --accent-red: #e87b7b
         --accent-cyan: #6cc7d4, --accent-magenta: #c084d4, --accent-blue: #7aa2ff
         --workspace-neutral: #8a847a, --workspace-red: #e87b7b, --workspace-orange: #ff7a47
         --workspace-green: #5ec26a, --workspace-yellow: #e8b86c, --workspace-cyan: #6cc7d4
         --workspace-blue: #7aa2ff, --workspace-purple: #c084d4
         --window-opacity-bg: rgba(11,10,9,0.88)
       - Additional cssVars beyond the 27 required (these pass schema validation and get injected by applyThemeOverrides):
         --focus-soft: rgba(255,91,31,0.14), --focus-hover: #ff7a47
         --role-planner: #ff5b1f, --role-executor: #6cc7d4, --role-reviewer: #e8b86c
         --role-watcher: #8a847a, --role-user: #5ec26a
         --font-display: "Poppins", system-ui, sans-serif
         --sidebar-w: 280px, --titlebar-height: 38px, --pane-header-height: 28px
       - ansi: 16 hex values per UI-SPEC xterm ANSI table:
         [#1a1714, #e87b7b, #5ec26a, #e8b86c, #7aa2ff, #c084d4, #6cc7d4, #c4beb5,
          #5a554d, #ff7070, #7ad68a, #f0c87c, #99b8ff, #d49ae4, #8ad4de, #f5f1ea]
       - cursor: #ff5b1f, cursorText: #0b0a09, selection: rgba(255,91,31,0.25)
       Use the exact JSON from RESEARCH Code Examples section as the reference.

    4. Add @font-face declarations to apps/voss-app/src/index.css — insert AFTER the @import "./styles/variant-b.css" line, BEFORE the @theme inline block:
       Two @font-face rules for Poppins (font-weight 500, 600), font-style normal,
       src url('/fonts/poppins-500.woff2') format('woff2'), font-display: swap.
       Do NOT add any Google Fonts link tag or @import url() — blocked by CSP per D-09 and RESEARCH Finding 1.
  </action>
  <verify>
    <automated>ls -la apps/voss-app/public/fonts/poppins-*.woff2 && node -e "const t=require('./apps/voss-app/src/themes/bundled/voss-ignite.json'); const s=require('./apps/voss-app/src/themes/schema'); const r=s.validateTheme(t); if(!r.ok){console.error(r.error);process.exit(1)} console.log('Schema OK, ansi count:', t.ansi.length)"</automated>
  </verify>
  <acceptance_criteria>
    - File apps/voss-app/src/themes/bundled/voss-ignite.json exists and passes validateTheme()
    - All 27 REQUIRED_CSS_VARS keys present in cssVars
    - ansi array has exactly 16 hex entries
    - cursor, cursorText, selection fields present
    - Extra tokens (--focus-soft, --role-*, --font-display, --sidebar-w, --titlebar-height) present in cssVars
    - poppins-500.woff2 and poppins-600.woff2 each > 10KB
    - index.css contains two @font-face rules for Poppins 500 and 600 with local src paths
    - No Google Fonts URL anywhere in index.css or index.html
  </acceptance_criteria>
  <done>Voss Ignite JSON validates against schema. Poppins fonts bundled locally. @font-face rules in index.css.</done>
</task>

<task type="auto">
  <name>Task 2: Register Ignite in theme catalog and set as default</name>
  <files>
    apps/voss-app/src/themes/themeCatalog.ts,
    apps/voss-app/src/themes/themeRuntime.ts,
    apps/voss-app/src/themes/__tests__/voss-ignite.test.ts
  </files>
  <read_first>
    apps/voss-app/src/themes/themeCatalog.ts,
    apps/voss-app/src/themes/themeRuntime.ts,
    apps/voss-app/src/themes/schema.ts
  </read_first>
  <action>
    1. In themeCatalog.ts:
       - Add import: import vossIgnite from './bundled/voss-ignite.json'
       - Add 'voss-ignite' to BUNDLED_THEME_IDS array (first position, before 'variant-b')
       - Add 'voss-ignite': vossIgnite as Theme to BUNDLED_BY_ID record
       - Update BundledThemeId type (it derives from BUNDLED_THEME_IDS, so automatic)

    2. In themeRuntime.ts:
       - Change DEFAULT_THEME on line 11 from getBundledTheme('variant-b')! to getBundledTheme('voss-ignite')!
       Per D-09: Ignite is the default; Variant B preserved as fallback.

    3. Create test file apps/voss-app/src/themes/__tests__/voss-ignite.test.ts:
       - Import validateTheme and REQUIRED_CSS_VARS from schema
       - Import vossIgnite from ../bundled/voss-ignite.json
       - Test: "voss-ignite passes schema validation" — call validateTheme(vossIgnite), assert ok: true
       - Test: "contains all REQUIRED_CSS_VARS" — iterate REQUIRED_CSS_VARS, assert each key exists in vossIgnite.cssVars
       - Test: "ansi has 16 entries" — assert vossIgnite.ansi.length === 16
       - Test: "has A12 extra tokens" — assert cssVars contains --focus-soft, --focus-hover, --role-planner, --role-executor, --role-reviewer, --role-watcher, --role-user, --font-display, --sidebar-w, --titlebar-height
       - Test: "WCAG contrast: --focus on --bg-0" — import contrastRatio, assert contrastRatio('#ff5b1f', '#0b0a09') >= 3.0 (large text / interactive element minimum)
       - Test: "default theme is voss-ignite" — import themeRuntime, assert getCommittedTheme().id === 'voss-ignite'
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run --grep "voss-ignite" 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - themeCatalog.ts imports voss-ignite.json and lists 'voss-ignite' in BUNDLED_THEME_IDS
    - BUNDLED_BY_ID contains 'voss-ignite' entry
    - getBundledTheme('voss-ignite') returns a valid Theme
    - themeRuntime.ts DEFAULT_THEME uses 'voss-ignite'
    - All voss-ignite tests pass
    - Existing theme tests still pass (variant-b remains in catalog)
    - pnpm --filter voss-app test passes with zero regressions
  </acceptance_criteria>
  <done>Voss Ignite registered in theme catalog, set as default. Variant B preserved. Schema conformance tests green. Full test suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Font file download | One-time download of woff2 from Google Fonts CDN during development |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-A12-01 | Tampering | Font file integrity | accept | One-time dev download; fonts are static assets served locally; no runtime fetch |
| T-A12-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan |
</threat_model>

<verification>
pnpm --filter voss-app test — all tests green including new voss-ignite tests.
grep -r "fonts.googleapis.com" apps/voss-app/ — returns 0 matches (CSP compliance).
</verification>

<success_criteria>
1. Voss Ignite theme JSON validates against schema with all 27 REQUIRED_CSS_VARS.
2. Poppins woff2 files bundled locally in public/fonts/.
3. @font-face declarations in index.css reference local paths.
4. Theme catalog exports 13 bundled themes (12 existing + Ignite).
5. Default theme is voss-ignite.
6. All existing tests pass with no regressions.
</success_criteria>

<output>
Create `.planning/phases/A12-voss-app-ade-visual-redesign/A12-01-SUMMARY.md` when done
</output>
