# Shell integration (OSC 133 capture)

`voss shell-init --shell zsh|bash|fish` prints a snippet that lets the Voss PTY
reader (`archive/voss-ade/crates/voss-app-core/src/pty/reader.rs`, frozen) see command boundaries,
exit codes, cwd, and argv text in a terminal pane. It is the capture half of
Observe (S3).

## What the snippet emits

| Hook | Sequence | Meaning |
|---|---|---|
| prompt start | `ESC ] 133 ; A BEL` | prompt begins |
| prompt end | `ESC ] 133 ; B BEL` | prompt ends, input begins |
| command start (`preexec`) | `ESC ] 133 ; C BEL` then `ESC ] 1337 ; voss-cmd={json} BEL` | command begins; JSON is `{"cmd_id","argv_text","cwd"}` |
| command end (`precmd`) | `ESC ] 133 ; D ; <exit> BEL` | command finished with exit code |
| every prompt | `ESC ] 7 ; file://<host><cwd> BEL` | current working directory |

`cmd_id` is a UUID4. The hooks use the Python interpreter that generated the
snippet, with isolated stdlib-only startup, to encode command metadata as JSON.
Quotes, Unicode, and multiline commands retain their original text.

## Install

```sh
# zsh (~/.zshrc)
eval "$(voss shell-init --shell zsh)"

# bash (~/.bashrc)
eval "$(voss shell-init --shell bash)"

# fish (~/.config/fish/config.fish)
voss shell-init --shell fish | source
```

Source it **last**, after any prompt theme: the `133;B` mark is appended to
`PROMPT`/`PS1` (zsh/bash) or wrapped around `fish_prompt`, and a theme that
rebuilds the prompt after sourcing would drop it.

## Gating

The snippet is inert unless `VOSS_EMBEDDED=1` is set — outside Voss panes it
installs no hooks and emits nothing. The desktop app sets `VOSS_EMBEDDED=1`
only when the setup-screen toggle is on. New Bash, Zsh, and Fish panes then
run the matching `voss shell-init` command before user input. This requires
`voss` on the shell's PATH. Existing panes keep their current hooks until reopened.
Sourcing twice is idempotent; no shell startup files are edited.

## Reader behavior

- Output evidence = the display bytes between `133;C` and `133;D`, capped at
  256 KiB (first 192 KiB + last 64 KiB, `truncated=true` when anything was
  dropped).
- `duration_ms` is measured from `133;C` to `133;D`. Missing `C` from an
  external emitter produces zero duration.
- A `133;D` with no open capture (e.g. the first prompt after spawn) is
  ignored.
- OSC sequences split across PTY reads are buffered until complete. An
  unterminated sequence exceeding 64 KiB passes through as display bytes so
  malformed output cannot hide the terminal indefinitely.

## Edge behavior (supported / unsupported)

- **Pipeline `a | b`**: one command event; `argv_text` is the full pipeline
  text; exit code is the pipeline's (`$?` / `$status`; use `pipefail`/`pipestatus`
  semantics of your shell to change what that is).
- **Background job `sleep 5 &`**: recorded when the foreground command line
  returns, not when the job reaps. Job-completion events are unsupported.
- **Nested shell (`zsh -c ...`, `ssh`, `tmux`)**: produces its own events only
  if the snippet is sourced inside that shell too. Non-interactive `sh -c`
  subshells never emit.
- **bash**: a DEBUG trap records the first command after each prompt; shell
  history supplies the full command line, falling back to `BASH_COMMAND` when
  history is unavailable. The capture hook runs before existing prompt commands
  so they cannot overwrite the command's exit status. With history disabled,
  compound-command text may contain only the first simple command.
- **fish**: `133;B` requires wrapping `fish_prompt`; if no `fish_prompt`
  function exists at source time the `B` mark is skipped (A/C/D still work).

## Verify

```sh
voss shell-init --shell zsh        # prints the snippet
VOSS_EMBEDDED=1 zsh -c 'source <(voss shell-init --shell zsh); _voss_precmd; _voss_preexec "echo hi"; _voss_precmd' | cat -v
# expect: ^[]133;A^G ^[]7;file://... ^[]133;C^G ^[]1337;voss-cmd={...}^G ^[]133;D;0^G
```

Reader unit tests lived in the archived app crate (scanner, tracker
lifecycle, truncation head/tail, wire format).

## Enrollment and recovery

Enable shell integration in setup, open a repository terminal, then run
`voss observe enable --repo .`. Observation settings expose the same enrollment.
A command run before enrollment does not permanently disable the pane: capture
resumes on its next command after enrollment. Pause/disable rejects queued capture.

`voss observe status --repo .` shows capture state and BOS backlog;
`voss observe events --repo . --tail 20` lists stored command events.
Subdirectories, symlinks, and linked worktrees use canonical Git identity.
Commands outside the pane's enrolled worktree are rejected. `.voss/observe.yml`
can exclude paths, restrict command prefixes, and lower the output cap; invalid
policy fails closed. Output and argv are redacted before storage.

Transient delivery failures retain at most 200 events per pane and retry once a
second, preserving event IDs. Closing a pane disposes its queue; restart persistence
is S9. The status bar reports queue overflow. BOS delivery runs after ingestion,
retries failures with bounded backoff, and recovers pending rows at server startup.
`voss observe reconcile --repo .` remains available for explicit replay.

See [S3 verification](s3-observe-verification.md) for checked behavior and limits.
