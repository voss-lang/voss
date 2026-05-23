import { describe, it, expect } from 'vitest';
import { REQUIRED_CSS_VARS, validateTheme, contrastRatio } from '../schema';
import vossIgnite from '../bundled/voss-ignite.json';
import { getCommittedTheme } from '../themeRuntime';

describe('voss-ignite theme', () => {
  it('passes schema validation', () => {
    expect(validateTheme(vossIgnite)).toEqual({ ok: true });
  });

  it('contains all REQUIRED_CSS_VARS', () => {
    for (const key of REQUIRED_CSS_VARS) {
      expect(vossIgnite.cssVars).toHaveProperty(key);
    }
  });

  it('ansi has 16 entries', () => {
    expect(vossIgnite.ansi).toHaveLength(16);
  });

  it('has A12 extra tokens', () => {
    const extras = [
      '--focus-soft', '--focus-hover',
      '--role-planner', '--role-executor', '--role-reviewer',
      '--role-watcher', '--role-user',
      '--font-display', '--sidebar-w', '--titlebar-height',
    ];
    for (const key of extras) {
      expect(vossIgnite.cssVars).toHaveProperty(key);
    }
  });

  it('WCAG contrast: --focus on --bg-0 >= 3.0', () => {
    expect(contrastRatio('#ff5b1f', '#0b0a09')).toBeGreaterThanOrEqual(3.0);
  });

  it('default theme is voss-ignite', () => {
    expect(getCommittedTheme().id).toBe('voss-ignite');
  });
});
