package voss

import (
	"context"
	"runtime"
	"testing"
	"time"
)

// TestIntegrationSSEOrdering asserts the real fake-turn stream delivers
// server.connected first, session.idle last, with typed plan/stream.delta/final
// between.
func TestIntegrationSSEOrdering(t *testing.T) {
	c := requireShared(t)
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	id, err := c.CreateSession(ctx, ".")
	if err != nil {
		t.Fatalf("CreateSession: %v", err)
	}
	ch, err := c.Events(ctx, id)
	if err != nil {
		t.Fatalf("Events: %v", err)
	}
	if err := c.PostMessage(ctx, id, "hi", ""); err != nil {
		t.Fatalf("PostMessage: %v", err)
	}

	var got []string
	deadline := time.After(30 * time.Second)
loop:
	for {
		select {
		case ev, ok := <-ch:
			if !ok {
				break loop
			}
			got = append(got, ev.eventType())
			if ev.eventType() == "session.idle" {
				break loop
			}
		case <-deadline:
			t.Fatalf("timed out; got %v", got)
		}
	}

	if len(got) < 3 {
		t.Fatalf("got %d events %v, want >=3", len(got), got)
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

// TestIntegrationSSECancel opens a real stream (no turn posted, so it idles open
// after server.connected), cancels mid-stream, and asserts the channel closes
// and no goroutine leaks.
func TestIntegrationSSECancel(t *testing.T) {
	c := requireShared(t)
	base := runtime.NumGoroutine()

	ctx, cancel := context.WithCancel(context.Background())
	id, err := c.CreateSession(ctx, ".")
	if err != nil {
		t.Fatalf("CreateSession: %v", err)
	}
	ch, err := c.Events(ctx, id)
	if err != nil {
		t.Fatalf("Events: %v", err)
	}

	select {
	case ev, ok := <-ch:
		if !ok || ev.eventType() != "server.connected" {
			t.Fatalf("first event = %v ok=%t, want server.connected", ev, ok)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("did not receive server.connected")
	}
	cancel()

	deadline := time.After(5 * time.Second)
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
	leaked := true
	for i := 0; i < 60; i++ {
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
