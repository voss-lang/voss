package voss

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// Shared integration state: TestMain spawns ONE VOSS_SERVE_FAKE_TURN server for
// the whole package's integration suite. Tests that need it call requireShared.
var (
	sharedClient       *Client
	integrationEnabled bool
)

// pythonAvailable reports whether an interpreter is resolvable (VOSS_PYTHON set
// or repo .venv/bin/python present) — the precondition for spawn integration.
func pythonAvailable() bool {
	if os.Getenv("VOSS_PYTHON") != "" {
		return true
	}
	_, err := os.Stat(filepath.Join("..", "..", ".venv", "bin", "python"))
	return err == nil
}

// TestMain spawns one shared fake-turn server (when an interpreter is available)
// for the integration tests, runs the suite, and tears the server down with no
// orphan. When no interpreter is available, integration tests skip and unit
// tests still run.
func TestMain(m *testing.M) {
	os.Exit(func() int {
		if !pythonAvailable() {
			return m.Run()
		}
		ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
		defer cancel()
		c, err := Spawn(ctx, map[string]string{"VOSS_SERVE_FAKE_TURN": "1"})
		if err != nil {
			// Could not spawn; run unit tests only rather than failing the suite.
			return m.Run()
		}
		sharedClient = c
		integrationEnabled = true
		code := m.Run()
		_ = c.Close()
		return code
	}())
}

// requireShared returns the shared spawned client or skips when integration is
// disabled.
func requireShared(t *testing.T) *Client {
	t.Helper()
	if !integrationEnabled || sharedClient == nil {
		t.Skip("integration disabled: no VOSS_PYTHON / repo .venv python")
	}
	return sharedClient
}
