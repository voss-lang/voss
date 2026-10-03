package main

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	voss "github.com/vosslang/voss/sdk/go"
)

func TestParseArgsAcceptsFlagsEitherSideOfCommand(t *testing.T) {
	dir := t.TempDir()
	for _, args := range [][]string{
		{"--attach", "http://x", "--token", "t", "--cwd", dir, "doctor"},
		{"doctor", "--attach", "http://x", "--token", "t", "--cwd", dir},
	} {
		o, err := parseArgs(args)
		if err != nil {
			t.Fatalf("parseArgs(%v): %v", args, err)
		}
		if o.cmd != "doctor" || o.attach != "http://x" || o.token != "t" || o.cwd != dir {
			t.Fatalf("parseArgs(%v) = %+v", args, o)
		}
	}
}

func TestParseArgsRejectsBadInput(t *testing.T) {
	for _, args := range [][]string{{"chatty"}, {"doctor", "extra"}, {"--nope", "doctor"}} {
		if _, err := parseArgs(args); err == nil {
			t.Fatalf("parseArgs(%v) accepted bad input", args)
		}
	}
}

func TestNoCommandOpensChat(t *testing.T) {
	o, err := parseArgs([]string{"--model", "m1"})
	if err != nil || o.cmd != "chat" || o.model != "m1" {
		t.Fatalf("parseArgs = %+v, err = %v", o, err)
	}
}

func TestTokenDefaultsToEnv(t *testing.T) {
	t.Setenv("VOSS_TUI_TOKEN", "from-env")
	o, err := parseArgs([]string{"doctor"})
	if err != nil || o.token != "from-env" {
		t.Fatalf("token = %q, err = %v", o.token, err)
	}
}

func TestReadSavedSessionsNewestFirstSkippingBadFiles(t *testing.T) {
	dir := t.TempDir()
	sessions := filepath.Join(dir, ".voss", "sessions")
	if err := os.MkdirAll(sessions, 0o755); err != nil {
		t.Fatal(err)
	}
	files := map[string]string{
		"old.json":    `{"id":"old","name":"first","updated_at":"2026-09-01T00:00:00","total_cost_usd":0.5,"turns":[{},{}]}`,
		"new.json":    `{"id":"new","name":"second","updated_at":"2026-09-20T00:00:00","turns":[{}]}`,
		"broken.json": `{"id":`,
		"noid.json":   `{"name":"missing id"}`,
		"notes.txt":   `{"id":"txt"}`,
	}
	for name, body := range files {
		if err := os.WriteFile(filepath.Join(sessions, name), []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
	}

	got := readSavedSessions(dir)
	if len(got) != 2 || got[0].Id != "new" || got[1].Id != "old" {
		t.Fatalf("sessions = %+v, want new then old", got)
	}
	if got[1].Turns != 2 || got[1].TotalCostUsd != 0.5 {
		t.Fatalf("old session = %+v, want 2 turns and $0.5", got[1])
	}
}

func TestSessionsWithNoSessionDirectory(t *testing.T) {
	dir := t.TempDir()
	var out bytes.Buffer
	if code := run(context.Background(), []string{"sessions", "--cwd", dir}, &out, &out); code != 0 {
		t.Fatalf("exit %d: %s", code, out.String())
	}
	if !strings.Contains(out.String(), "no saved sessions for "+dir) {
		t.Fatalf("output = %q", out.String())
	}
}

func TestDoctorOverAttachSendsCwdAndReturnsServerExitCode(t *testing.T) {
	dir := t.TempDir()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer tok" {
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		if r.URL.Path != "/doctor" || r.URL.Query().Get("cwd") != dir {
			t.Errorf("request = %s, want /doctor?cwd=%s", r.URL, dir)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"auth_source": "env", "auth_detail": "key set", "has_provider": true,
			"default_model": "m", "exit_code": 1,
			"checks": []map[string]string{
				{"name": "python", "status": "OK", "detail": "3.12"},
				{"name": "git", "status": "FAIL", "detail": "missing", "fix": "install git"},
			},
		})
	}))
	defer srv.Close()

	var out, errOut bytes.Buffer
	code := run(context.Background(), []string{"--attach", srv.URL, "--token", "tok", "--cwd", dir, "doctor"}, &out, &errOut)
	if code != 1 {
		t.Fatalf("exit %d, want the server's 1; stderr: %s", code, errOut.String())
	}
	for _, want := range []string{"auth      : env — key set", "✓ python", "✗ git", "→ install git"} {
		if !strings.Contains(out.String(), want) {
			t.Fatalf("output missing %q:\n%s", want, out.String())
		}
	}
}

func TestDoctorReportsAuthFailure(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		_, _ = w.Write([]byte(`{"detail":"bad token"}`))
	}))
	defer srv.Close()

	var out, errOut bytes.Buffer
	if code := run(context.Background(), []string{"--attach", srv.URL, "doctor"}, &out, &errOut); code != 1 {
		t.Fatalf("exit %d, want 1", code)
	}
	if !strings.Contains(errOut.String(), "HTTP 401: bad token") {
		t.Fatalf("stderr = %q", errOut.String())
	}
}

// TestDoctorSpawned runs doctor against a real `voss serve`. It needs VOSS_BIN
// or the repo's .venv/bin/voss and skips otherwise.
func TestDoctorSpawned(t *testing.T) {
	if os.Getenv("VOSS_BIN") == "" {
		venv, _ := filepath.Abs(filepath.Join("..", ".venv", "bin", "voss"))
		if _, err := os.Stat(venv); err != nil {
			t.Skip("no VOSS_BIN and no repo .venv/bin/voss")
		}
		t.Setenv("VOSS_BIN", venv)
	}
	var out, errOut bytes.Buffer
	code := run(context.Background(), []string{"doctor", "--cwd", t.TempDir()}, &out, &errOut)
	if code != 0 && code != 1 {
		t.Fatalf("exit %d; stderr: %s", code, errOut.String())
	}
	if !strings.Contains(out.String(), "auth      :") {
		t.Fatalf("output = %q; stderr: %s", out.String(), errOut.String())
	}
}

func TestInterruptExitsQuietly(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	var out, errOut bytes.Buffer
	if code := run(ctx, []string{"--attach", "http://127.0.0.1:1", "doctor"}, &out, &errOut); code != 130 {
		t.Fatalf("exit %d, want 130", code)
	}
	if errOut.Len() != 0 {
		t.Fatalf("stderr = %q, want nothing", errOut.String())
	}
}

func TestConnectUsesDispatcherPythonWithoutVossOnPath(t *testing.T) {
	root, _ := filepath.Abs("..")
	python := filepath.Join(root, ".venv", "bin", "python")
	if _, err := os.Stat(python); err != nil {
		t.Skip("no repo Python environment")
	}
	t.Setenv("VOSS_SERVER_PYTHON", python)
	t.Setenv("VOSS_BIN", "")
	t.Setenv("PYTHONPATH", root)
	t.Setenv("VOSS_SERVE_FAKE_TURN", "1")
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()
	cwd := t.TempDir()
	client, err := connect(ctx, options{cwd: cwd})
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()
	if _, err := client.OpenSession(ctx, voss.SessionOptions{Cwd: cwd}); err != nil {
		t.Fatal(err)
	}
}

func TestConnectPreservesExplicitServerOverride(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "missing-voss")
	t.Setenv("VOSS_SERVER_PYTHON", "unused-python")
	t.Setenv("VOSS_BIN", missing)
	_, err := connect(context.Background(), options{cwd: t.TempDir()})
	if err == nil || !strings.Contains(err.Error(), "missing-voss") {
		t.Fatalf("VOSS_BIN override was not used: %v", err)
	}
}

func TestHelpSucceedsWithoutServer(t *testing.T) {
	var out, errOut bytes.Buffer
	code := run(context.Background(), []string{"--help"}, &out, &errOut)
	if code != 0 || errOut.Len() != 0 || !strings.Contains(out.String(), "usage: voss-tui ") || !strings.Contains(out.String(), "resume ID") {
		t.Fatalf("help exit=%d stdout=%q stderr=%q", code, out.String(), errOut.String())
	}
}
