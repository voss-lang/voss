package voss

import (
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"sync"
	"time"
)

// spawnHandshakeTimeout is 60s: litellm's cold import can take tens of seconds.
const spawnHandshakeTimeout = 60 * time.Second

// stderrTailBytes bounds how much server stderr is kept for handshake errors.
const stderrTailBytes = 8 << 10

// SpawnError is returned when launching or handshaking with `voss serve` fails.
type SpawnError struct{ Err error }

func (e *SpawnError) Error() string {
	if e.Err == nil {
		return "spawn voss serve failed"
	}
	return "spawn voss serve: " + e.Err.Error()
}

func (e *SpawnError) Unwrap() error { return e.Err }

// LaunchOptions configures Spawn. The zero value resolves the executable,
// inherits the caller's working directory and waits 60s for the handshake.
type LaunchOptions struct {
	Executable       string
	Cwd              string
	Env              map[string]string
	HandshakeTimeout time.Duration
}

// resolveExecutable picks the explicit path, else VOSS_BIN, else `voss` on
// PATH, the same order as the Rust and TypeScript SDKs (docs/sdk.md).
func resolveExecutable(explicit string) string {
	if explicit != "" {
		return explicit
	}
	if v := os.Getenv("VOSS_BIN"); v != "" {
		return v
	}
	return "voss"
}

// stderrTail keeps the end of the server's stderr so it can be reported on a
// failed handshake without ever writing to the consumer's terminal.
type stderrTail struct {
	mu sync.Mutex
	b  []byte
}

func (t *stderrTail) Write(p []byte) (int, error) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.b = append(t.b, p...)
	if len(t.b) > stderrTailBytes {
		t.b = t.b[len(t.b)-stderrTailBytes:]
	}
	return len(p), nil
}

func (t *stderrTail) String() string {
	t.mu.Lock()
	defer t.mu.Unlock()
	return string(t.b)
}

// Spawn launches `voss serve --port 0`, reads its handshake, and returns a
// Client bound to the ephemeral port. stdin is held open as a heartbeat: the
// server exits when it closes.
func Spawn(ctx context.Context, opts LaunchOptions) (*Client, error) {
	cmd := exec.CommandContext(ctx, resolveExecutable(opts.Executable), "serve", "--port", "0")
	cmd.Dir = opts.Cwd
	cmd.Env = append(os.Environ(), "PYDANTIC_DISABLE_PLUGINS=1", "LITELLM_LOCAL_MODEL_COST_MAP=true")
	for k, v := range opts.Env {
		cmd.Env = append(cmd.Env, k+"="+v)
	}
	stderr := &stderrTail{}
	cmd.Stderr = stderr
	// Bounds Wait when a wrapper's child (the npm launcher's Python) still holds stderr.
	cmd.WaitDelay = 2 * time.Second

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

	timeout := opts.HandshakeTimeout
	if timeout == 0 {
		timeout = spawnHandshakeTimeout
	}
	hs, err := readHandshake(stdout, timeout)
	if err != nil {
		_ = stdinW.Close()
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
		return nil, &SpawnError{Err: fmt.Errorf("%w; stderr:\n%s", err, stderr)}
	}

	// Drain the rest of stdout so a full pipe never blocks the server.
	go func() { _, _ = io.Copy(io.Discard, stdout) }()

	c := AttachClient(hs.baseURL(), hs.Token)
	c.spawn = &spawnState{cmd: cmd, stdinW: stdinW, pid: cmd.Process.Pid}
	return c, nil
}
