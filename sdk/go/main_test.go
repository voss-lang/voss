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

// testExecutable resolves the server for integration tests: VOSS_BIN, else the
// repo's .venv/bin/voss. ok=false disables integration.
func testExecutable() (string, bool) {
	if v := os.Getenv("VOSS_BIN"); v != "" {
		return v, true
	}
	p, err := filepath.Abs(filepath.Join("..", "..", ".venv", "bin", "voss"))
	if err != nil {
		return "", false
	}
	if _, err := os.Stat(p); err != nil {
		return "", false
	}
	return p, true
}

func fakeTurnOptions() LaunchOptions {
	exe, _ := testExecutable()
	return LaunchOptions{Executable: exe, Env: map[string]string{"VOSS_SERVE_FAKE_TURN": "1"}}
}

// TestMain spawns one shared fake-turn server (when an interpreter is available)
// for the integration tests, runs the suite, and tears the server down with no
func TestMain(m *testing.M) {
	os.Exit(func() int {
		if _, ok := testExecutable(); !ok {
			return m.Run()
		}
		ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
		defer cancel()
		c, err := Spawn(ctx, fakeTurnOptions())
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
		t.Skip("integration disabled: no VOSS_BIN / repo .venv/bin/voss")
	}
	return sharedClient
}
