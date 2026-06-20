# BOSR-05 Plan: Control-Plane Read Model

**Status:** Ready for execution
**Wave:** 4
**Type:** code
**Requirements:** BOSR-06

## Objective

Expose a local read model that desktop and future web surfaces can consume
without syncing raw code, prompts, transcripts, or sensitive records by default.

## Scope

Implement:
- read-model builder over local BOS event, decision, and outcome ledgers
- summaries for team/project/task/session/agent-run entities
- recommendation queue view over shadow recommendations
- privacy-safe fields only
- tests proving raw content is excluded

Do not implement:
- web app
- remote sync
- accounts/tenants
- external integrations

## Read First

- `.planning/phases/BOS7-web-control-plane-boundary/BOS7-RESPONSIBILITY-MAP.md`
- `.planning/phases/BOS6-privacy-governance-and-tenant-boundaries/BOS6-GOVERNANCE-SPEC.md`
- `.planning/phases/BOS8-team-project-and-work-model/BOS8-CONTEXT.md`
- `.planning/BOS-EVENT-SCHEMA.md`

## Acceptance Criteria

1. Read model groups events by trace, session, task, and swarm where present.
2. Recommendation queue exposes only safe metadata and decision refs.
3. No raw prompt, transcript, file content, credentials, or production records
   appear in read-model outputs.
4. Offline/local operation works without backend services.
5. Tests cover empty ledgers, projected session/run events, swarm events, and
   recommendation rows.

## Verification

```bash
pytest tests/harness/test_bos_read_model.py \
  tests/harness/test_bos_shadow_recommendations.py -q
python3 -m py_compile voss/harness/bos_read_model.py
```
