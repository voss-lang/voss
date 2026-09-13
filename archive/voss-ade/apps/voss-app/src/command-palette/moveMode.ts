export type MoveDirection = 'left' | 'right' | 'up' | 'down';

const KEYS: Record<string, MoveDirection> = {
  h: 'left',
  j: 'down',
  k: 'up',
  l: 'right',
  a: 'left',
  s: 'down',
  w: 'up',
  d: 'right',
  ArrowLeft: 'left',
  ArrowDown: 'down',
  ArrowUp: 'up',
  ArrowRight: 'right',
};

export function moveModeDirection(key: string): MoveDirection | null {
  return KEYS[key] ?? KEYS[key.toLowerCase()] ?? null;
}
