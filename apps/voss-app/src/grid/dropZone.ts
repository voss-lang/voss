import type { Rect } from './geometry';

export type DropZone = 'left' | 'right' | 'top' | 'bottom' | 'center';

export const EDGE_FRAC = 0.25; // Zed's drop_target_size; outer quarter = edge

/** Zone for a pointer at (x, y) inside rect. Caller guarantees containment. */
export function zoneAt(rect: Rect, x: number, y: number): DropZone {
  const rx = (x - rect.x) / rect.w; // 0..1
  const ry = (y - rect.y) / rect.h;
  const d: [number, DropZone][] = [
    [rx, 'left'],
    [1 - rx, 'right'],
    [ry, 'top'],
    [1 - ry, 'bottom'],
  ];
  d.sort((a, b) => a[0] - b[0]);
  return d[0][0] < EDGE_FRAC ? d[0][1] : 'center';
}

/** First rect containing (x, y), or null. rects = drag-start snapshot. */
export function hitTest(
  rects: ReadonlyMap<string, Rect>,
  x: number,
  y: number,
): string | null {
  for (const [id, r] of rects) {
    if (x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h) return id;
  }
  return null;
}

/** Highlight rect for a zone: half the pane for edges, whole pane for center. */
export function highlightRect(rect: Rect, zone: DropZone): Rect {
  switch (zone) {
    case 'left':
      return { ...rect, w: rect.w / 2 };
    case 'right':
      return { ...rect, x: rect.x + rect.w / 2, w: rect.w / 2 };
    case 'top':
      return { ...rect, h: rect.h / 2 };
    case 'bottom':
      return { ...rect, y: rect.y + rect.h / 2, h: rect.h / 2 };
    case 'center':
      return rect;
  }
}
