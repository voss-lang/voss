import { test } from "node:test";
import assert from "node:assert/strict";
import { parseAmount } from "../src/money.ts";

test("AC-1 valid amounts", () => {
  assert.equal(parseAmount("$1,234.50"), 1234.5);
  assert.equal(parseAmount("1234"), 1234);
  assert.equal(parseAmount("-$5.00"), -5);
  assert.equal(parseAmount("  $0.99 "), 0.99);
  assert.equal(parseAmount("$1,000,000"), 1000000);
});

test("AC-2 invalid amounts throw", () => {
  for (const bad of ["abc", "", "$", "1,23", "12.345"]) {
    assert.throws(() => parseAmount(bad), Error, bad);
  }
});
