import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  registerScrollbackProvider,
  unregisterScrollbackProvider,
  getScrollbackSnapshot,
  _resetForTest,
} from '../scrollbackRegistry';

/**
 * A6-03 Task 1 — scrollback registry tests.
 *
 * Pure JS — no xterm, no DOM.
 */

beforeEach(() => _resetForTest());

describe('scrollbackRegistry — registration', () => {
  it('returns empty map when no providers registered', () => {
    const snap = getScrollbackSnapshot();
    expect(snap.size).toBe(0);
  });

  it('returns lines from registered providers', () => {
    registerScrollbackProvider('a', () => ['$ ls', 'file.txt']);
    registerScrollbackProvider('b', () => ['$ pwd', '/repo']);
    const snap = getScrollbackSnapshot();
    expect(snap.get('a')).toEqual(['$ ls', 'file.txt']);
    expect(snap.get('b')).toEqual(['$ pwd', '/repo']);
  });

  it('unregister removes the provider', () => {
    registerScrollbackProvider('a', () => ['line']);
    unregisterScrollbackProvider('a');
    const snap = getScrollbackSnapshot();
    expect(snap.has('a')).toBe(false);
  });

  it('re-registering the same id replaces the provider', () => {
    registerScrollbackProvider('a', () => ['old']);
    registerScrollbackProvider('a', () => ['new']);
    const snap = getScrollbackSnapshot();
    expect(snap.get('a')).toEqual(['new']);
  });
});

describe('scrollbackRegistry — last-2k capping', () => {
  it('caps output to the last `limit` lines (default 2000)', () => {
    const lines = Array.from({ length: 3000 }, (_, i) => `line-${i}`);
    registerScrollbackProvider('a', () => lines);
    const snap = getScrollbackSnapshot();
    const result = snap.get('a')!;
    expect(result).toHaveLength(2000);
    expect(result[0]).toBe('line-1000');
    expect(result[1999]).toBe('line-2999');
  });

  it('respects custom limit', () => {
    const lines = Array.from({ length: 100 }, (_, i) => `line-${i}`);
    registerScrollbackProvider('a', () => lines);
    const snap = getScrollbackSnapshot(10);
    expect(snap.get('a')).toHaveLength(10);
    expect(snap.get('a')![0]).toBe('line-90');
  });

  it('returns all lines when under limit', () => {
    registerScrollbackProvider('a', () => ['one', 'two']);
    const snap = getScrollbackSnapshot();
    expect(snap.get('a')).toEqual(['one', 'two']);
  });
});

describe('scrollbackRegistry — error isolation', () => {
  it('skips a throwing provider without blocking others', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    registerScrollbackProvider('bad', () => {
      throw new Error('xterm disposed');
    });
    registerScrollbackProvider('good', () => ['ok']);

    const snap = getScrollbackSnapshot();

    expect(snap.has('bad')).toBe(false);
    expect(snap.get('good')).toEqual(['ok']);
    expect(warn).toHaveBeenCalledTimes(1);
    warn.mockRestore();
  });
});
