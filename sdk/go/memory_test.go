package voss

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestMemoryEncodesQueryAndDecodesHits(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		q := r.URL.Query()
		if r.URL.Path != "/memory" || q.Get("cwd") != "/project with spaces" || q.Get("q") != "retry & backoff" || q.Get("top_k") != "3" {
			t.Errorf("unexpected request: %s", r.URL)
		}
		_, _ = w.Write([]byte(`{"summary":"2 notes","hits":[{"source":"note","locator":"notes/retry.md","score":0.75,"excerpt":"retry after 5s"}]}`))
	}))
	defer srv.Close()
	report, err := AttachClient(srv.URL, "test").Memory(context.Background(), "/project with spaces", "retry & backoff", 3)
	if err != nil || report.Summary != "2 notes" || len(report.Hits) != 1 || report.Hits[0].Excerpt != "retry after 5s" {
		t.Fatalf("Memory = %+v, %v", report, err)
	}
}
