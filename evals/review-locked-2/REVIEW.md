# Review labels to check

For each pair: edit the fixture's label, set gold, then flag=reviewed (or flag=ambiguous).

## rv-044 AC-3

> A project can turn the security principle off with disable: [security], and a test covers it.

- draft gold: `insufficient_evidence`
- note: The general disable path would remove it, but no test of disabling security is added; the added test only checks the defaults.

## rv-056 AC-1

> A swarm role with agent cursor runs a task in its worktree and exits.

- draft gold: `insufficient_evidence`
- note: The catalog entry exists, but nothing was run, and its binary cursor-agent differs from the key, against the catalog's binary == key convention.

## rv-057 AC-1

> Without textual installed, voss chat falls back to plain mode with no traceback.

- draft gold: `insufficient_evidence`
- note: Catching Exception makes a fallback plausible, but no run shows voss chat starting.

## rv-058 AC-1

> voss eval --stub reports the same token counts as before on the golden tasks.

- draft gold: `insufficient_evidence`
- note: count_tokens changes from len/4 to len/3, but complete() still estimates with // 4 and no eval was run; it could be read as contradicted.

## rv-063 AC-2

> The unknown-agent error lists the known agents.

- draft gold: `supported`
- note: The unchanged UnknownAgentError message in resolve_agent_argv joins known_agents(); the existing swarm agent tests passed.
