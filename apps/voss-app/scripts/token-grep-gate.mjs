#!/usr/bin/env node
// VCKP-10 — A12 token-only enforcement gate.
//
// The cockpit (and the V14 attention surface) may consume ONLY the A12 Ignite
// token set: the `cssVars` of themes/bundled/voss-ignite.json plus the base
// custom properties DEFINED in src/index.css (the shipped A12 foundation,
// e.g. --font-mono/--font-ui). Any other `--xxx` custom property referenced
// via var() or declared in the scanned files fails the gate (exit 1).
//
// Comments are stripped before scanning so header prose can name tokens
// without self-invalidating the gate. CLI flag strings like "--model" are NOT
// matched — only `var(--x)` references and `--x:` declarations count.

import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

// --- Allowed set -------------------------------------------------------------
const ignite = JSON.parse(
  readFileSync(join(root, 'src/themes/bundled/voss-ignite.json'), 'utf8'),
);
const allowed = new Set(Object.keys(ignite.cssVars));
const indexCss = readFileSync(join(root, 'src/index.css'), 'utf8');
for (const m of indexCss.matchAll(/(--[a-zA-Z0-9-]+)\s*:/g)) allowed.add(m[1]);

// --- Scan targets ------------------------------------------------------------
const SCAN_DIRS = ['src/org/cockpit', 'src/org/attention'];
const files = SCAN_DIRS.flatMap((d) => {
  try {
    return readdirSync(join(root, d))
      .filter((f) => /\.(css|tsx|ts)$/.test(f))
      .map((f) => join(root, d, f));
  } catch {
    return [];
  }
});

function stripComments(text) {
  return text
    .replace(/\/\*[\s\S]*?\*\//g, '') // CSS/TS block comments
    .split('\n')
    .filter((line) => !/^\s*\/\//.test(line)) // TS line comments
    .join('\n');
}

const offenders = [];
for (const file of files) {
  const text = stripComments(readFileSync(file, 'utf8'));
  const used = new Set();
  // var(--x) references (CSS and inline style strings in TSX).
  for (const m of text.matchAll(/var\(\s*(--[a-zA-Z0-9-]+)/g)) used.add(m[1]);
  // --x: declarations (a NEW custom property definition is also a violation).
  // Must start a declaration (after { ; or line start) so BEM modifier classes
  // with pseudo-selectors (.attn-btn--deny:hover) don't false-positive.
  for (const m of text.matchAll(/(?:^|[{;])\s*(--[a-zA-Z0-9-]+)\s*:/gm)) {
    used.add(m[1]);
  }
  for (const tok of used) {
    if (!allowed.has(tok)) {
      offenders.push(`${relative(root, file)}: ${tok}`);
    }
  }
}

if (offenders.length > 0) {
  console.error('[token-grep-gate] FOREIGN tokens (not in the A12 Ignite set):');
  for (const o of offenders) console.error(`  ${o}`);
  process.exit(1);
}
console.log(
  `[token-grep-gate] OK — ${files.length} files scanned, A12 tokens only (${allowed.size} allowed).`,
);
