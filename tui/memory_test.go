package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	voss "github.com/vosslang/voss/sdk/go"
)

func TestMemoryAndRecallUseWorkspaceEndpoint(t *testing.T) {
	cwd := t.TempDir()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		q := r.URL.Query()
		if r.URL.Path != "/memory" || q.Get("cwd") != cwd {
			t.Errorf("unexpected request: %s", r.URL)
		}
		switch q.Get("q") {
		case "retry policy":
			if q.Get("top_k") != "2" {
				t.Errorf("top_k = %s", q.Get("top_k"))
			}
			_, _ = w.Write([]byte(`{"summary":"2 notes","hits":[{"source":"note","locator":"retry.md","score":0.75,"excerpt":"retry\nafter 5s"}]}`))
		case "outage":
			w.WriteHeader(http.StatusServiceUnavailable)
			_, _ = w.Write([]byte(`{"detail":"Memory backend unavailable"}`))
		default:
			_, _ = w.Write([]byte(`{"summary":"2 notes","hits":[]}`))
		}
	}))
	defer srv.Close()
	client := voss.AttachClient(srv.URL, "test")
	for _, tc := range []struct {
		name string
		args []string
		want string
	}{
		{"/memory", nil, "2 notes"},
		{"/recall", []string{"retry", "policy", "--top", "2"}, "[note] retry.md  (score 0.75)\n  retry after 5s"},
		{"/recall", []string{"unknown"}, "(no hits)"},
	} {
		msg := memoryCommand(context.Background(), client, cwd, tc.name, tc.args)().(slashOutputMsg)
		if msg.stdout != tc.want || msg.stderr != "" {
			t.Fatalf("%s %v = %+v", tc.name, tc.args, msg)
		}
	}
	msg := memoryCommand(context.Background(), client, cwd, "/recall", []string{"outage"})().(errMsg)
	if !strings.Contains(errText(msg.err), "Memory backend unavailable") {
		t.Fatal(msg.err)
	}
}

func TestMemoryCommandsRejectUnsupportedOptionsBeforeRequest(t *testing.T) {
	for _, args := range [][]string{nil, {"--top"}, {"query", "--top", "0"}, {"query", "--top", "51"}, {"query", "--top", "many"}, {"query", "--source", "note"}} {
		msg := memoryCommand(context.Background(), nil, ".", "/recall", args)().(slashOutputMsg)
		if !strings.HasPrefix(msg.stderr, "usage: /recall") {
			t.Fatalf("args %v: %+v", args, msg)
		}
	}
	msg := memoryCommand(context.Background(), nil, ".", "/memory", []string{"--source", "note"})().(slashOutputMsg)
	if msg.stderr != "usage: /memory" {
		t.Fatalf("unsupported memory filter: %+v", msg)
	}
}
