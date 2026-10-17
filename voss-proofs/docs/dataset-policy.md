# Dataset policy

Every scenario in `benchmarks/` must meet all of these rules.

- **Provenance.** `[meta]` must set `synthetic` and `origin`. `origin` says who made the scenario, when, and from what source.
- **No sensitive data.** No credentials, tokens, private transcripts, production records, personal data or health information may appear anywhere in a scenario. That covers fixtures, prompts, patches and hidden tests.
- **Real-world examples must be authorized and sanitized.** A scenario taken from a real repository must name that repository and a pinned commit in `origin`. Its license must allow redistribution. Copied code keeps its original license header.
- **Hidden tests stay hidden.** Never reference `hidden/` from a prompt, fixture or visible test.
- **Validated before use.** `proofs validate` must pass: the oracle is verified and the null run is not. A scenario that fails validation is not part of any reported result.
- **Labels on frozen data don't change.** Locked datasets (the J3 and J4 evals in the Voss repo, and future `dataset = "locked"` sets here) are never relabeled or tuned against after freezing. A correction goes into a new versioned dataset.
- **Voss trajectories.** Session records and event streams from live runs can contain model output about the fixture. They stay in local `results/`, which is git-ignored, and are not committed unless reviewed.
