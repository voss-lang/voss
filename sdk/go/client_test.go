package voss

import (
	"context"
	"errors"
	"os"
	"syscall"
	"testing"
	"time"
)

// requirePython skips the test when no interpreter is resolvable (VOSS_PYTHON
// unset and repo .venv/bin/python absent), so spawn integration tests are
// hermetic-optional.
func requirePython(t *testing.T) {
	t.Helper()
	if !pythonAvailable() {
		t.Skip("no VOSS_PYTHON and no repo .venv/bin/python; skipping spawn integration")
	}
}

// drainTurn reads from the SSE channel until session.idle (or timeout) and
// returns the set of event types seen.
func drainTurn(t *testing.T, ch <-chan TypedEvent, timeout time.Duration) map[string]bool {
	t.Helper()
	seen := map[string]bool{}
	deadline := time.After(timeout)
	for {
		select {
		case ev, ok := <-ch:
			if !ok {
				return seen
			}
			seen[ev.eventType()] = true
			if ev.eventType() == "session.idle" {
				return seen
			}
		case <-deadline:
			t.Fatalf("timed out draining turn; saw %v", seen)
			return seen
		}
	}
}

// TestSpawnNoOrphan spawns a FAKE_TURN server, runs a full turn end-to-end, then
// asserts Close() leaves no orphan (the recorded PID is gone).
func TestSpawnNoOrphan(t *testing.T) {
	requirePython(t)
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	c, err := Spawn(ctx, map[string]string{"VOSS_SERVE_FAKE_TURN": "1"})
	if err != nil {
		t.Fatalf("Spawn: %v", err)
	}
	if c.spawn == nil || c.spawn.cmd == nil || c.spawn.pid == 0 {
		t.Fatalf("spawnState not populated: %+v", c.spawn)
	}
	pid := c.spawn.pid

	// End-to-end fake turn: create -> open stream -> post -> drain to idle.
	id, err := c.CreateSession(ctx, ".")
	if err != nil {
		t.Fatalf("CreateSession: %v", err)
	}
	ch, err := c.Events(ctx, id)
	if err != nil {
		t.Fatalf("Events: %v", err)
	}
	if err := c.PostMessage(ctx, id, "hello", ""); err != nil {
		t.Fatalf("PostMessage: %v", err)
	}
	seen := drainTurn(t, ch, 30*time.Second)
	if !seen["final"] {
		t.Fatalf("fake turn produced no final event; saw %v", seen)
	}

	if err := c.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	// PID must be gone (reaped). Signal 0 probes liveness without killing.
	proc, _ := os.FindProcess(pid)
	if err := proc.Signal(syscall.Signal(0)); err == nil {
		t.Fatalf("process %d still alive after Close (orphan)", pid)
	}

	// Idempotent: a second Close is a no-op.
	if err := c.Close(); err != nil {
		t.Fatalf("second Close: %v", err)
	}
}

// TestSpawnBadInterpreter asserts a bad VOSS_PYTHON yields a typed *SpawnError
// promptly (no hang).
func TestSpawnBadInterpreter(t *testing.T) {
	t.Setenv("VOSS_PYTHON", "/nonexistent/voss-python-does-not-exist")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	start := time.Now()
	c, err := Spawn(ctx, nil)
	if elapsed := time.Since(start); elapsed > 25*time.Second {
		t.Fatalf("Spawn hung %v on a bad interpreter", elapsed)
	}
	if c != nil {
		_ = c.Close()
		t.Fatal("expected nil client on bad interpreter")
	}
	var se *SpawnError
	if !errors.As(err, &se) {
		t.Fatalf("error %v is not *SpawnError", err)
	}
}

// TestAttachRoundTrip spawns a server, builds an AttachClient from its base/token,
// does a REST round-trip, and asserts the attach client's Close() does NOT kill
// the still-running spawned server.
func TestAttachRoundTrip(t *testing.T) {
	requirePython(t)
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	srv, err := Spawn(ctx, map[string]string{"VOSS_SERVE_FAKE_TURN": "1"})
	if err != nil {
		t.Fatalf("Spawn: %v", err)
	}
	defer srv.Close()

	att := AttachClient(srv.baseURL, srv.token)
	if att.spawn != nil {
		t.Fatal("attach client must own no child")
	}
	if _, err := att.CreateSession(ctx, "."); err != nil {
		t.Fatalf("attach CreateSession: %v", err)
	}
	// Attach Close is a no-op for the process.
	if err := att.Close(); err != nil {
		t.Fatalf("attach Close: %v", err)
	}
	// The spawned server is still alive: a follow-up call succeeds.
	if _, err := srv.CreateSession(ctx, "."); err != nil {
		t.Fatalf("spawned server died after attach Close: %v", err)
	}
}
