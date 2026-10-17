import { test } from "node:test";
import assert from "node:assert/strict";
import { parseAmount } from "../src/money.ts";

test("plain integer", () => {
  assert.equal(parseAmount("1234"), 1234);
});
