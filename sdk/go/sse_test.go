package voss

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"runtime"
	"testing"
	"time"
)

// sseFrame writes one SSE frame (event: + data: + blank line) and flushes.
func sseFrame(w http.ResponseWriter, fl http.Flusher, typ, data string) {
	_, _ = io.WriteString(w, "event: "+typ+"\n")
	_, _ = io.WriteString(w, "data: "+data+"\n")
	_, _ = io.WriteString(w, "\n")
	fl.Flush()
}

// TestIntegrationSSEOrdering asserts the consumer delivers a canned fake-turn
// sequence in order: server.connected first, session.idle last, with typed
// plan/stream.delta/final between. Uses an httptest SSE stub; the real
// fake-turn-server variant runs via TestMain in Plan 06.
func TestIntegrationSSEOrdering(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		fl, ok := w.(http.Flusher)
		if !ok {
			t.Errorf("ResponseWriter is not a Flusher")
			return
		}
		// A ping comment + id: line must be ignored by the parser.
		_, _ = io.WriteString(w, ": ping\n\n")
		fl.Flush()
		sseFrame(w, fl, "server.connected", `{"v":1,"type":"server.connected"}`)
		sseFrame(w, fl, "plan", `{"v":1,"type":"plan","confidence":0.9,"steps":[],"cost_usd":0.0}`)
		sseFrame(w, fl, "stream.delta", `{"v":1,"type":"stream.delta","text":"hi"}`)
		sseFrame(w, fl, "final", `{"v":1,"type":"final","text":"done","confidence":0.9,"cost_usd":0.0}`)
		sseFrame(w, fl, "session.idle", `{"v":1,"type":"session.idle","session_id":"sess-1"}`)
	}))
	t.Cleanup(srv.Close)

	c := AttachClient(srv.URL, "good")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	ch, err := c.Events(ctx, "sess-1")
	if err != nil {
		t.Fatalf("Events: %v", err)
	}

	var got []string
	for ev := range ch {
		got = append(got, ev.eventType())
	}

	if len(got) < 5 {
		t.Fatalf("got %d events %v, want >=5", len(got), got)
	}
	if got[0] != "server.connected" {
		t.Fatalf("first = %q, want server.connected", got[0])
	}
	if got[len(got)-1] != "session.idle" {
		t.Fatalf("last = %q, want session.idle", got[len(got)-1])
	}
	want := map[string]bool{"plan": false, "stream.delta": false, "final": false}
	for _, typ := range got {
		if _, ok := want[typ]; ok {
			want[typ] = true
		}
	}
	for typ, seen := range want {
		if !seen {
			t.Fatalf("missing typed event %q in %v", typ, got)
		}
	}
}

// TestIntegrationSSECancel asserts cancelling the context ends delivery: the
// channel closes within a deadline, no panic, and the goroutine count returns
// to baseline (no leak).
func TestIntegrationSSECancel(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		fl, ok := w.(http.Flusher)
		if !ok {
			return
		}
		sseFrame(w, fl, "server.connected", `{"v":1,"type":"server.connected"}`)
		// Hold the stream open until the client disconnects (ctx cancel).
		<-r.Context().Done()
	}))
	t.Cleanup(srv.Close)

	c := AttachClient(srv.URL, "good")
	base := runtime.NumGoroutine()

	ctx, cancel := context.WithCancel(context.Background())
	ch, err := c.Events(ctx, "sess-1")
	if err != nil {
		t.Fatalf("Events: %v", err)
	}

	// Receive the first event, then cancel mid-stream.
	select {
	case ev, ok := <-ch:
		if !ok || ev.eventType() != "server.connected" {
			t.Fatalf("first event = %v ok=%t, want server.connected", ev, ok)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("did not receive first event")
	}
	cancel()

	// Channel must close within the deadline.
	deadline := time.After(2 * time.Second)
	for {
		select {
		case _, ok := <-ch:
			if !ok {
				goto closed
			}
		case <-deadline:
			t.Fatal("channel not closed after cancel")
		}
	}
closed:
	// Goroutine count returns to baseline (allow a small slack + settle time).
	leaked := true
	for i := 0; i < 40; i++ {
		if runtime.NumGoroutine() <= base+2 {
			leaked = false
			break
		}
		time.Sleep(50 * time.Millisecond)
	}
	if leaked {
		t.Fatalf("goroutine leak: base=%d now=%d", base, runtime.NumGoroutine())
	}
}
