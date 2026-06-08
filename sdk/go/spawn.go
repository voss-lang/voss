package voss

import (
	"context"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// spawnHandshakeTimeout bounds the wait for the server's handshake line. It is
// 60s (not 20s) because `voss serve` eagerly imports litellm, whose cold import
// (remote cost-map fetch + import-tree compile) can take tens of seconds on a
// first run — V13.2-06 hit exactly this. Spawn also sets
// LITELLM_LOCAL_MODEL_COST_MAP=true to drop the network fetch.
const spawnHandshakeTimeout = 60 * time.Second

// SpawnError is returned when launching or handshaking with `voss serve` fails.
type SpawnError struct{ Err error }

func (e *SpawnError) Error() string {
	if e.Err == nil {
		return "spawn voss serve failed"
	}
	return "spawn voss serve: " + e.Err.Error()
}

func (e *SpawnError) Unwrap() error { return e.Err }

// interpreterPath resolves the Python interpreter for `voss serve` using the
// fixed chain VOSS_PYTHON → repo .venv/bin/python (relative to the working
// directory) → "python3". The chain is fixed (no caller-supplied path), so
// there is no path/command injection. Mirrors crates/voss-tui/src/server.rs
// python_path().
func interpreterPath() string {
	if v := os.Getenv("VOSS_PYTHON"); v != "" {
		return v
	}
	cand := filepath.Join("..", "..", ".venv", "bin", "python")
	if _, err := os.Stat(cand); err == nil {
		if abs, err := filepath.Abs(cand); err == nil {
			return abs
		}
		return cand
	}
	return "python3"
}

// Spawn launches `<python> -m voss.cli serve --port 0`, reads its handshake, and
// returns a Client bound to the ephemeral loopback port + token with its
// spawnState populated. The child's stdin is piped and held open as the
// EOF-supervision heartbeat (never written); Close() (or ctx cancel) tears the
// child down with no orphan. extraEnv augments the inherited environment (e.g.
// VOSS_SERVE_FAKE_TURN=1 for tests).
//
// Spawn POPULATES the spawnState struct DEFINED in client.go by Plan 03 — it
// does not re-declare the type.
func Spawn(ctx context.Context, extraEnv map[string]string) (*Client, error) {
	python := interpreterPath()
	cmd := exec.CommandContext(ctx, python, "-m", "voss.cli", "serve", "--port", "0")
	cmd.Env = append(os.Environ(), "LITELLM_LOCAL_MODEL_COST_MAP=true")
	for k, v := range extraEnv {
		cmd.Env = append(cmd.Env, k+"="+v)
	}
	cmd.Stderr = os.Stderr

	stdinW, err := cmd.StdinPipe()
	if err != nil {
		return nil, &SpawnError{Err: err}
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		_ = stdinW.Close()
		return nil, &SpawnError{Err: err}
	}
	if err := cmd.Start(); err != nil {
		_ = stdinW.Close()
		return nil, &SpawnError{Err: err}
	}

	hs, err := readHandshake(stdout, spawnHandshakeTimeout)
	if err != nil {
		_ = stdinW.Close()
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
		return nil, &SpawnError{Err: err}
	}

	// Drain the rest of stdout so a full pipe never blocks the server.
	go func() { _, _ = io.Copy(io.Discard, stdout) }()

	c := AttachClient(hs.baseURL(), hs.Token)
	c.spawn = &spawnState{cmd: cmd, stdinW: stdinW, pid: cmd.Process.Pid}
	return c, nil
}
