import { test } from 'node:test';
import assert from 'node:assert';
import { add } from './calc.ts';

test('add(1, 2) === 3', () => {
  assert.strictEqual(add(1, 2), 3);
});
