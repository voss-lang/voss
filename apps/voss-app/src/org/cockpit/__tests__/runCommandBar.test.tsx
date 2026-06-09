import { describe, it, expect, vi, afterEach } from 'vitest';
import { render } from 'solid-js/web';
import {
  assembleRunSpec,
  validateAutoStart,
  type RunIntakeState,
  type RunSpec,
} from '../runIntake';

// RunCommandBar imports `@tauri-apps/api/core` for its default terminal launcher.
// The start-path tests inject mocks, so `invoke` is never called — stub it so the
// module import resolves under jsdom.
vi.mock('@tauri-apps/api/core', () => ({ invoke: vi.fn() }));

import RunCommandBar from '../RunCommandBar';
import {
  cardToPane,
  cardToSessionNode,
  __resetBridgeMaps,
} from '../../model/bridge';

describe('runIntake — validate + assemble (pure)', () => {
  it('assembleRunSpec carries all intake fields into the spec', () => {
    const state: RunIntakeState = {
      goal: 'Refactor auth',
      mode: 'Auto',
      team: 'core',
      scope: 'tests/**',
      budget: 5,
      target: 'native',
    };
    const spec = assembleRunSpec(state);
    expect(spec).toEqual({
      goal: 'Refactor auth',
      mode: 'Auto',
      team: 'core',
      scope: 'tests/**',
      budget: 5,
      target: 'native',
    });
  });

  describe('validate', () => {
    it('blocks Auto with missing budget (reason mentions budget)', () => {
      const result = validateAutoStart({
        mode: 'Auto',
        budget: undefined,
        scope: 'x',
      });
      expect(result.ok).toBe(false);
      expect(result.reason).toMatch(/budget/i);
    });

    it('blocks Auto with missing scope (reason mentions scope)', () => {
      const result = validateAutoStart({
        mode: 'Auto',
        budget: 5,
        scope: undefined,
      });
      expect(result.ok).toBe(false);
      expect(result.reason).toMatch(/scope/i);
    });

    it('allows Auto when both budget and scope are present', () => {
      const result = validateAutoStart({
        mode: 'Auto',
        budget: 5,
        scope: 'tests/**',
      });
      expect(result).toEqual({ ok: true });
    });

    it('never blocks Plan/Edit regardless of budget/scope', () => {
      expect(validateAutoStart({ mode: 'Plan' })).toEqual({ ok: true });
      expect(validateAutoStart({ mode: 'Edit' })).toEqual({ ok: true });
      expect(
        validateAutoStart({ mode: 'Plan', budget: undefined, scope: undefined }),
      ).toEqual({ ok: true });
      expect(
        validateAutoStart({ mode: 'Edit', budget: undefined, scope: undefined }),
      ).toEqual({ ok: true });
    });
  });
});
