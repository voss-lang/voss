# summarize-diff fixture

Seed repo for the SKL-03 `summarize-diff` skill test. A downstream test
introduces an unstaged modification to this file before invoking the skill,
then asserts the emitted PR summary contains `## Title`, `## Summary`, and
`## Changes`.
