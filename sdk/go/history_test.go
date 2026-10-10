package voss

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestSessionHistoryAndClear(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.Method == http.MethodGet && r.URL.Path == "/session/saved/history":
			_, _ = w.Write([]byte(`{"v":1,"turns":[{"role":"user","content":"hello"},{"role":"assistant","content":"hi"}]}`))
		case r.Method == http.MethodPost && r.URL.Path == "/session/saved/clear":
			w.WriteHeader(http.StatusNoContent)
		case r.URL.Path == "/sessions/saved":
			_, _ = w.Write([]byte(`{"sessions":[{"id":"saved","first_task":"hello"}]}`))
		default:
			w.WriteHeader(http.StatusNotFound)
			_, _ = w.Write([]byte(`{"detail":"session not found"}`))
		}
	}))
	defer srv.Close()
	c, ctx := AttachClient(srv.URL, "test"), context.Background()
	history, err := c.GetHistory(ctx, "saved")
	if err != nil || len(history) != 2 || history[0].Role != User || history[0].Content != "hello" || history[1].Role != Assistant {
		t.Fatalf("GetHistory = %+v, %v", history, err)
	}
	if err := c.ClearHistory(ctx, "saved"); err != nil {
		t.Fatal(err)
	}
	saved, err := c.ListSavedSessions(ctx, "/project")
	if err != nil || len(saved) != 1 || saved[0].FirstTask != "hello" {
		t.Fatalf("ListSavedSessions = %+v, %v", saved, err)
	}
	_, historyErr := c.GetHistory(ctx, "missing")
	for _, err := range []error{historyErr, c.ClearHistory(ctx, "missing")} {
		var ve *VossError
		if !errors.As(err, &ve) || ve.Status != http.StatusNotFound {
			t.Fatalf("missing session error = %v", err)
		}
	}
}
