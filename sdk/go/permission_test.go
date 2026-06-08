package voss

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newPermissionStub returns an httptest server for POST /session/:id/permission
// that replies with the given status JSON when authed, else 401. Per CONTEXT
// D-09 the route contract is verified via direct HTTP (FAKE_TURN emits no
// permission.updated, so a live gate is manual/deferred).
func newPermissionStub(t *testing.T, wantToken, status string) *httptest.Server {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer "+wantToken {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			_, _ = io.WriteString(w, `{"v":1,"detail":"unauthorized"}`)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = io.WriteString(w, `{"v":1,"status":"`+status+`"}`)
	}))
	t.Cleanup(srv.Close)
	return srv
}

// TestPermissionAllow asserts an allow reply maps to stale=false (the reply was
// recorded). The gate-outcome (allowed→tool runs) is observed over SSE with a
// real provider — manual/deferred per D-09.
func TestPermissionAllow(t *testing.T) {
	srv := newPermissionStub(t, "good", "ok")
	c := AttachClient(srv.URL, "good")
	stale, err := c.PermissionReply(context.Background(), "sess-1", "ab12", "a")
	if err != nil {
		t.Fatalf("PermissionReply: %v", err)
	}
	if stale {
		t.Fatal("allow reply returned stale=true, want false")
	}
}

// TestPermissionDeny asserts a deny reply maps to stale=false (recorded), a
// reply to an already-resolved/unknown id maps to stale=true (not an error),
// and an unauthorized reply surfaces a typed *VossError.
func TestPermissionDeny(t *testing.T) {
	ctx := context.Background()

	// Deny recorded -> ok -> stale=false.
	denySrv := newPermissionStub(t, "good", "ok")
	c := AttachClient(denySrv.URL, "good")
	stale, err := c.PermissionReply(ctx, "sess-1", "ab12", "d")
	if err != nil {
		t.Fatalf("deny PermissionReply: %v", err)
	}
	if stale {
		t.Fatal("deny reply returned stale=true, want false")
	}

	// Already-resolved/unknown id -> stale -> stale=true, no error.
	staleSrv := newPermissionStub(t, "good", "stale")
	c = AttachClient(staleSrv.URL, "good")
	stale, err = c.PermissionReply(ctx, "sess-1", "gone", "a")
	if err != nil {
		t.Fatalf("stale PermissionReply: %v", err)
	}
	if !stale {
		t.Fatal("stale-id reply returned stale=false, want true")
	}

	// Unauthorized -> typed *VossError{401}.
	c = AttachClient(staleSrv.URL, "wrong")
	_, err = c.PermissionReply(ctx, "sess-1", "ab12", "a")
	var ve *VossError
	if !errors.As(err, &ve) || ve.Status != 401 {
		t.Fatalf("unauthorized reply err = %v, want *VossError{401}", err)
	}
}
