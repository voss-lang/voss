package voss

import (
	"context"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

// spawnHandshakeTimeout is 60s: litellm's cold import can take tens of seconds.
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

// interpreterPath resolves Python: VOSS_PYTHON → repo .venv/bin/python →
// "python3". Fixed chain, no caller input. Mirrors voss-tui python_path().
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

// Spawn launches `voss serve --port 0`, reads its handshake, and returns a
// Client bound to the ephemeral port. stdin is held open as the EOF heartbeat;
// Close()/ctx-cancel tears it down. extraEnv augments the environment.
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
