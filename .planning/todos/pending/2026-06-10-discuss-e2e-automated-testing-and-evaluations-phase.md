---
created: 2026-06-10T17:39:59.411Z
title: Discuss e2e automated testing and evaluations phase
area: testing
files: []
---

## Problem

Voss has unit/integration tests per phase, but nothing proving the system actually works end-to-end with real model behavior. Need a dedicated phase for:

- E2E automated testing — full pipeline runs (CLI → harness → model → output) exercised automatically, not just isolated modules
- Evaluations (evals) — measure that model responses and agent functionality are actually correct/useful, not just that code paths don't crash

Goal: prove model + functionality works, not just that tests pass. This is a discussion-stage idea — scope, eval framework choice, what surfaces to cover, and pass/fail criteria all TBD.

## Solution

TBD. Start with /gsd-discuss-phase (or /gsd-ai-integration-phase for the eval-design side). Candidate inputs: existing test suites under tests/, /e2e skill for test-surface mapping, gsd-eval-planner for eval rubric design.
