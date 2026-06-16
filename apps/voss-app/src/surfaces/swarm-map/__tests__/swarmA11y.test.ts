// V24-07 (VADE2-07) — Swarm Map reduced-motion a11y gate. jsdom does not
// evaluate media queries, so the guard is asserted on the stylesheet source
// (same readFileSync discipline as cockpit a11y.test.tsx): every `animation:`
// declaration MUST live inside the reduced-motion double-guard block. RED until
// Task 2 lands the guarded keyframes.

import { describe, it, expect } from 'vitest';
// @ts-ignore -- node builtin available in the vitest runtime; app tsconfig is browser-lib only.
import { readFileSync } from 'node:fs';

// Path relative to the vitest root (apps/voss-app — vitest.config.ts).
const rawSwarmCss: string = readFileSync(
  'src/surfaces/swarm-map/swarmMap.css',
  'utf8',
);

describe('swarmMap.css — A8 reduced-motion guard', () => {
  it('contains the reduced-motion media guard', () => {
    expect(rawSwarmCss).toContain('@media (not (prefers-reduced-motion: reduce))');
  });

  it('has no animation: declaration outside the reduced-motion guard block', () => {
    // Strip the sentinel-delimited guard block, then assert nothing animates.
    const stripped = rawSwarmCss.replace(
      /@media \(not \(prefers-reduced-motion: reduce\)\) \{[\s\S]*?\} \/\* end-reduced-motion-guard \*\//g,
      '',
    );
    // `animation-play-state` (a pause hook) is allowed; only `animation:` is gated.
    expect(stripped).not.toMatch(/animation\s*:/);
  });
});
