import { describe, it, expect } from 'vitest';
import { zoneAt, hitTest, highlightRect, EDGE_FRAC } from '../dropZone';
import type { Rect } from '../geometry';

const rect = (x: number, y: number, w: number, h: number): Rect => ({
  x,
  y,
  w,
  h,
});

const R = rect(100, 100, 200, 200);

describe('dropZone — zoneAt', () => {
  it('center hit in inner region', () => {
    expect(zoneAt(R, 200, 200)).toBe('center');
  });

  it('left edge band', () => {
    expect(zoneAt(R, 100 + R.w * 0.1, 200)).toBe('left');
  });

  it('right edge band', () => {
    expect(zoneAt(R, 100 + R.w * 0.95, 200)).toBe('right');
  });

  it('top edge band', () => {
    expect(zoneAt(R, 200, 100 + R.h * 0.1)).toBe('top');
  });

  it('bottom edge band', () => {
    expect(zoneAt(R, 200, 100 + R.h * 0.95)).toBe('bottom');
  });

  it('exact boundary at EDGE_FRAC is center (not edge)', () => {
    const x = R.x + R.w * EDGE_FRAC;
    expect(zoneAt(R, x, 200)).toBe('center');
  });

  it('corner determinism: left wins when equidistant', () => {
    // At top-left corner, rx=0 and ry=0 — both 0, sort stable → left first
    expect(zoneAt(R, R.x, R.y)).toBe('left');
  });
});

describe('dropZone — hitTest', () => {
  const rects = new Map([
    ['a', rect(0, 0, 100, 100)],
    ['b', rect(100, 0, 100, 100)],
  ]);

  it('inside returns pane id', () => {
    expect(hitTest(rects, 50, 50)).toBe('a');
    expect(hitTest(rects, 150, 50)).toBe('b');
  });

  it('outside returns null', () => {
    expect(hitTest(rects, -1, 50)).toBeNull();
    expect(hitTest(rects, 50, 200)).toBeNull();
  });

  it('right/bottom edges are exclusive (half-open)', () => {
    expect(hitTest(rects, 100, 50)).toBe('b');
    expect(hitTest(rects, 0, 100)).toBeNull();
    expect(hitTest(rects, 100, 100)).toBeNull();
  });
});

describe('dropZone — highlightRect', () => {
  it('left half', () => {
    expect(highlightRect(R, 'left')).toEqual({ ...R, w: 100 });
  });

  it('right half', () => {
    expect(highlightRect(R, 'right')).toEqual({ ...R, x: 200, w: 100 });
  });

  it('top half', () => {
    expect(highlightRect(R, 'top')).toEqual({ ...R, h: 100 });
  });

  it('bottom half', () => {
    expect(highlightRect(R, 'bottom')).toEqual({ ...R, y: 200, h: 100 });
  });

  it('center is full rect', () => {
    expect(highlightRect(R, 'center')).toEqual(R);
  });
});
