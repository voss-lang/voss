export const LOD_ZOOM = 0.6;
export const CHIP_LINES = 3;

export interface LineBuffer {
  length: number;
  getLine(y: number): { translateToString(trim?: boolean): string } | undefined;
}

export function lastLines(buffer: LineBuffer, n = CHIP_LINES): string[] {
  const out: string[] = [];
  for (let y = buffer.length - 1; y >= 0 && out.length < n; y -= 1) {
    const text = buffer.getLine(y)?.translateToString(true) ?? '';
    if (text.trim() !== '') out.unshift(text);
  }
  return out;
}

/** A plain keystroke meant for the focused terminal (no chords, no navigation) */
export function isTypingKey(e: KeyboardEvent): boolean {
  if (e.metaKey || e.ctrlKey || e.altKey) return false;
  return e.key.length === 1 || e.key === 'Enter';
}
