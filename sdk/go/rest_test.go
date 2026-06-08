package voss

import (
	"context"
	"errors"
	"sync"
	"testing"
	"time"
)

// TestVossError lives in errors_test.go; permission tests live in
// permission_test.go. These run against the shared TestMain fake-turn server.

// TestIntegrationRestRoundTrip exercises create(201) -> message(202) -> drain ->
// cost(200) -> delete(204) against the real server.
func TestIntegrationRestRoundTrip(t *testing.T) {
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
	if seen := drainTurn(t, ch, 30*time.Second); !seen["final"] {
		t.Fatalf("turn produced no final; saw %v", seen)
	}
	if _, err := c.Cost(ctx, id); err != nil {
		t.Fatalf("Cost: %v", err)
	}
	if err := c.DeleteSession(ctx, id); err != nil {
		t.Fatalf("DeleteSession: %v", err)
	}
}

// TestIntegration401 asserts a wrong bearer token yields *VossError{401}.
func TestIntegration401(t *testing.T) {
	c := requireShared(t)
	bad := AttachClient(c.baseURL, "wrong-token")
	_, err := bad.CreateSession(context.Background(), ".")
	var ve *VossError
	if !errors.As(err, &ve) || ve.Status != 401 {
		t.Fatalf("err = %v, want *VossError{401}", err)
	}
}

// TestBearerHeader asserts the correct token succeeds and a wrong token 401s
// against the real server (the bearer is attached via the single chokepoint).
func TestBearerHeader(t *testing.T) {
	c := requireShared(t)
	ctx := context.Background()
	if _, err := c.ListSessions(ctx); err != nil {
		t.Fatalf("good token ListSessions: %v", err)
	}
	bad := AttachClient(c.baseURL, "nope")
	_, err := bad.ListSessions(ctx)
	var ve *VossError
	if !errors.As(err, &ve) || ve.Status != 401 {
		t.Fatalf("wrong token err = %v, want *VossError{401}", err)
	}
}

// TestIntegration409 fires two concurrent PostMessage calls at one session and
// asserts exactly one *VossError{409} when the race is triggered. The fake turn
// can complete before the second post arrives, so the race is not always
// observable — retry a few times and skip (not fail) if it never triggers
// (RESEARCH Pitfall 7).
func TestIntegration409(t *testing.T) {
	c := requireShared(t)
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	for attempt := 0; attempt < 3; attempt++ {
		id, err := c.CreateSession(ctx, ".")
		if err != nil {
			t.Fatalf("CreateSession: %v", err)
		}

		var wg sync.WaitGroup
		errs := make([]error, 2)
		for i := 0; i < 2; i++ {
			wg.Add(1)
			go func(i int) {
				defer wg.Done()
				errs[i] = c.PostMessage(ctx, id, "hi", "")
			}(i)
		}
		wg.Wait()

		var ok, conflict int
		for _, e := range errs {
			if e == nil {
				ok++
				continue
			}
			var ve *VossError
			if errors.As(e, &ve) && ve.Status == 409 {
				conflict++
			} else {
				t.Fatalf("unexpected PostMessage error: %v", e)
			}
		}
		_ = c.DeleteSession(ctx, id)

		if conflict == 1 && ok == 1 {
			return // race observed, contract holds
		}
	}
	t.Skip("409 race not reliably triggerable on this machine (fake turn completes too fast)")
}
