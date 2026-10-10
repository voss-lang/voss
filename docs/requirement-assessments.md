# Requirement assessments

Voss can ask Jev whether a piece of work meets its acceptance criteria. Jev
looks at the diff, the code, and the check results, and answers once per
criterion. Voss shows the answers under the heading
"Requirement assessments (advisory)".

## What it does

Each criterion gets one of four results:

- **supported**: the evidence shows the criterion is met.
- **contradicted**: the evidence shows the criterion is not met.
- **unclear (abstained)**: Jev was not sure enough either way.
- **no answer**: Jev's answer for this criterion was missing or malformed.
  The other criteria keep their results.

Every result carries the criterion ID (such as `AC-1` or `S4.1`) and a packet
ID. The packet ID identifies the exact evidence Jev was given.

The results are advisory. They never approve, block, retry, or move a card.
They never change Reviewer B's verdict or its `conf` value. A failed check or
a scope violation still counts exactly as it did before. The existing review
gates stay in charge.

## Turning it on and off

It is off by default. To turn on the automatic checks for a project, add this
to `.voss/config.yml`:

```yaml
judgments:
  enabled: true
  review: shadow
```

You also need a Jev key in `TYPESAFE_API_KEY` or in the keychain. `review`
accepts only `off` and `shadow`. There is no `active` setting: the results
never decide anything.

`VOSS_JUDGMENTS=off` stops every Jev call, including `voss judge review`.
With it set, nothing is sent.

## Where it runs

1. **Swarm candidates.** This is the automatic path that runs in live use
   today. When a swarm task becomes a candidate and the project has
   `review: shadow`, Voss checks the candidate commit against the task goal in
   the background. The ownership check is passed in as the scope status. It
   never changes the candidate, the task, any gate, or integration. The result
   is saved per task.
2. **The board Done review.** This hook works and is covered by tests, but it
   stays inactive in live runs until the board's worker pipeline exists. No
   live card reaches Done yet, so there is nothing for it to check.
3. **`voss judge review`.** You run it on demand.

## Where you see it

To see the saved result for a swarm candidate:

```sh
voss judge review --swarm <swarm-id> --task <task-id> --saved
```

This reads the saved file only. It makes no request and needs no key.

To check something now, run `voss judge review`. It works whether or not
`review` is set in the project config, but it still needs a key and still
obeys `VOSS_JUDGMENTS=off`. It fails with an error instead of quietly skipping.

Your uncommitted changes, including new files:

```sh
voss judge review --criterion "adds a --dry-run flag" --criterion "logs each skipped file"
```

One commit:

```sh
voss judge review --ref 1a2b3c4 --criteria-file criteria.md
```

A swarm candidate, using its task goal as the criteria:

```sh
voss judge review --swarm <swarm-id> --task <task-id>
```

Options:

- `--criterion TEXT`: one criterion. Repeat it for more.
- `--criteria-file FILE`: one criterion per line. Bullets and numbers are
  removed. A line that starts with an ID such as `AC-3:` keeps that ID.
- `--checks FILE`: check results as a JSON list. Each item is either
  `{"name": "unit", "status": "passed"}` or the eval runner's
  `{"type": "unit", "pass": true, "detail": "..."}`. Allowed statuses are
  `passed`, `failed`, `skipped`, `not_run`, and `stale`. Anything else is
  rejected before a request is sent.
- `--run ROOT_ID`: also save the result to
  `.voss/sessions/<root_id>/judgments.json`, so `voss audit` shows it. The run
  must already exist.
- `--json`: print the full receipt as JSON.

`voss audit` shows saved results in its Judgments section, under
"Requirement assessments (advisory)".

## Reading the labels

A criterion shows **supported** only when Jev gives supported a probability of
0.80 or more. **contradicted** uses the same 0.80 cutoff. Anything below that is
**unclear (abstained)**. The line shows the probability next to the label, for
example `AC-1  supported  P(supported)=0.92  current`.

If the whole request fails, you see `not available:` and the reason. A failure
is never shown as a low number.

**stale: work changed since this was checked** means a file the check looked
at has been edited or deleted since. Voss does not re-check on its own. To
check again, run `voss judge review`, or wait for another Done review. A
check of a commit never goes stale, because a commit does not change.

## What is sent and stored

For a board review or `voss judge review`, Voss sends:

- the criteria;
- the diff, cut to fit the size limit;
- the start of each changed file, up to 200 lines per file;
- check names and statuses;
- Reviewer A's note, for board reviews.

That is the same evidence Reviewer B already receives.

For a swarm candidate, Voss sends the task goal, the candidate commit's diff
from its base, the code at that commit, and the ownership (scope) status.

Receipts store IDs, labels, probabilities, digests, and counts. They do not
store the criteria text, the diff, or the code. Board and `--run` results go in
`.voss/sessions/<root>/judgments.json`. Swarm candidate results go in
`.voss/swarm/<swarm-id>/reviews/<task-id>.json`.

## Cost

Each swarm candidate or Done review makes one request. Each review gets its
own cap: 4 calls and $0.01 by default. There is no total cap across
candidates or cards. Jev spend is not counted against `/budget`.

## Limits

- The board hook stays inactive in live runs until the board worker pipeline
  is built, which is planned for a later phase. Until then, swarm candidates
  are the only automatic path.
- Even once the board hook fires, live `voss board` runs use a placeholder
  Reviewer B that always passes. In those runs the assessment sits beside a
  placeholder reviewer, not a real one.
- A swarm candidate's criteria are its task goal. That is often a single
  requirement.
- Only checks of uncommitted work can go stale.
- `judgments.json` shows up in `voss session export`, the same way other
  files in a run folder that are not session nodes do.

## Recommendation

Whether to recommend `review: shadow` is pending the locked evaluation in
`evals/review/reports/review-release.md`.
