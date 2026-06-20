# BOSR Discussion Log: Behavioral OS Runtime Foundation

**Created:** 2026-06-20
**Source:** User reset request after BOS/BOSI planning drift.

## Discussion Summary

The previous BOS structure drifted into an oversized docs-first sequence:
BOS0-BOS18 held useful product, data, architecture, governance, and surface
knowledge, but too many rows were placeholders. BOSI then tried to add a
separate implementation track, which fixed the symptom only partially and made
the roadmap harder to reason about.

Ben's correction:
- Keep the knowledge.
- Stop expanding phase lists.
- Collapse the active Behavioral OS work back into one phase.
- Use the normal GSD sequence: discuss, research, plan, execute.
- Produce a traditional 3-6 plan implementation phase like the V-track and
  A-track, not a plans-to-plan structure.

## Resolution

Create one active phase:

`BOSR - Behavioral OS Runtime Foundation`

BOSR supersedes the active BOS0-BOS18/BOSI1-BOSI6 split. Existing BOS0-BOS9
artifacts and BOSI1 implementation code remain source material. BOS10-BOS18
and BOSI2-BOSI6 are retired as active placeholders.

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| D-01 | One active BOSR phase | Reduces plan bloat and restores normal GSD execution |
| D-02 | Preserve BOS0-BOS9 as source material | They contain useful product, schema, governance, and surface decisions |
| D-03 | Fold BOSI1 into BOSR | The event projector is real code and should seed the runtime phase |
| D-04 | Retire BOS10-BOS18 and BOSI2-BOSI6 as active rows | They were placeholders, not researched implementation plans |
| D-05 | Code-backed after BOSR-01 | BOSR-01 is reconciliation; BOSR-02..06 must change code/tests or validation artifacts |
| D-06 | No new coordination bus | V25 server/SSE swarm remains the event source and coordination substrate |
| D-07 | No online learning in BOSR | Shadow heuristics and offline evaluation precede learned/autonomous policy changes |
| D-08 | Private-by-default local substrate | Raw code, prompts, transcripts, and sensitive records do not sync by default |

## Next Step

Execute BOSR-02 after review: local BOS event ledger over the existing BOSI1
projection module.
