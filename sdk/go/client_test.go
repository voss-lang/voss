package voss

import (
	"context"
	"errors"
	"os"
	"strings"
	"syscall"
	"testing"
	"time"
)

// requireVoss skips spawn integration tests when no server executable resolves
// (VOSS_BIN unset and repo .venv/bin/voss absent).
func requireVoss(t *testing.T) {
	t.Helper()
	if _, ok := testExecutable(); !ok {
		t.Skip("no VOSS_BIN and no repo .venv/bin/voss; skipping spawn integration")
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
	requireVoss(t)
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	c, err := Spawn(ctx, fakeTurnOptions())
	if err != nil {
		t.Fatalf("Spawn: %v", err)
	}
	if c.spawn == nil || c.spawn.cmd == nil || c.spawn.pid == 0 {
		t.Fatalf("spawnState not populated: %+v", c.spawn)
	}
	pid := c.spawn.pid

	// End-to-end fake turn: create -> open stream -> post -> drain to idle.
	id, err := c.CreateSession(ctx, SessionOptions{Cwd: "."})
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

// TestSpawnBadExecutable asserts a missing executable yields a typed
// *SpawnError naming the path, promptly (no hang).
func TestSpawnBadExecutable(t *testing.T) {
	const bad = "/nonexistent/voss-does-not-exist"
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	start := time.Now()
	c, err := Spawn(ctx, LaunchOptions{Executable: bad})
	if elapsed := time.Since(start); elapsed > 25*time.Second {
		t.Fatalf("Spawn hung %v on a bad executable", elapsed)
	}
	if c != nil {
		_ = c.Close()
		t.Fatal("expected nil client on bad executable")
	}
	var se *SpawnError
	if !errors.As(err, &se) {
		t.Fatalf("error %v is not *SpawnError", err)
	}
	if !strings.Contains(err.Error(), bad) {
		t.Fatalf("error %q does not name %s", err, bad)
	}
}

// TestResolveExecutableOrder asserts explicit path, then VOSS_BIN, then `voss`
// on PATH, matching the Rust and TypeScript SDKs.
func TestResolveExecutableOrder(t *testing.T) {
	t.Setenv("VOSS_BIN", "/from/env/voss")
	if got := resolveExecutable("/explicit/voss"); got != "/explicit/voss" {
		t.Fatalf("explicit: got %q", got)
	}
	if got := resolveExecutable(""); got != "/from/env/voss" {
		t.Fatalf("VOSS_BIN: got %q", got)
	}
	t.Setenv("VOSS_BIN", "")
	if got := resolveExecutable(""); got != "voss" {
		t.Fatalf("PATH fallback: got %q", got)
	}
}

// TestAttachRoundTrip spawns a server, builds an AttachClient from its base/token,
// does a REST round-trip, and asserts the attach client's Close() does NOT kill
func TestAttachRoundTrip(t *testing.T) {
	requireVoss(t)
	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	srv, err := Spawn(ctx, fakeTurnOptions())
	if err != nil {
		t.Fatalf("Spawn: %v", err)
	}
	defer srv.Close()

	att := AttachClient(srv.baseURL, srv.token)
	if att.spawn != nil {
		t.Fatal("attach client must own no child")
	}
	if _, err := att.CreateSession(ctx, SessionOptions{Cwd: "."}); err != nil {
		t.Fatalf("attach CreateSession: %v", err)
	}
	// Attach Close is a no-op for the process.
	if err := att.Close(); err != nil {
		t.Fatalf("attach Close: %v", err)
	}
	// The spawned server is still alive: a follow-up call succeeds.
	if _, err := srv.CreateSession(ctx, SessionOptions{Cwd: "."}); err != nil {
		t.Fatalf("spawned server died after attach Close: %v", err)
	}
}
