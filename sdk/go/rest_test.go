package voss

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

// TestVossError lives in errors_test.go (Plan 02 implemented errors.go).

// newRESTStub returns an httptest server emulating the FAKE_TURN round-trip
// (create 201 / message 202 / cost 200 / delete 204) behind a bearer gate. When
// lastAuth is non-nil, each request's Authorization header is recorded there.
func newRESTStub(t *testing.T, wantToken string, lastAuth *string) *httptest.Server {
	t.Helper()
	h := func(w http.ResponseWriter, r *http.Request) {
		if lastAuth != nil {
			*lastAuth = r.Header.Get("Authorization")
		}
		if r.Header.Get("Authorization") != "Bearer "+wantToken {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			_, _ = io.WriteString(w, `{"v":1,"detail":"unauthorized"}`)
			return
		}
		switch {
		case r.Method == http.MethodPost && r.URL.Path == "/session":
			w.WriteHeader(http.StatusCreated)
			_, _ = io.WriteString(w, `{"v":1,"id":"sess-1","resumed":false}`)
		case r.Method == http.MethodPost && r.URL.Path == "/session/sess-1/message":
			w.WriteHeader(http.StatusAccepted)
			_, _ = io.WriteString(w, `{"v":1,"status":"accepted"}`)
		case r.Method == http.MethodGet && r.URL.Path == "/session/sess-1/cost":
			w.WriteHeader(http.StatusOK)
			_, _ = io.WriteString(w, `{"v":1,"total_usd":0.42,"turns":1}`)
		case r.Method == http.MethodDelete && r.URL.Path == "/session/sess-1":
			w.WriteHeader(http.StatusNoContent)
		default:
			w.WriteHeader(http.StatusNotFound)
			_, _ = io.WriteString(w, `{"v":1,"detail":"not found"}`)
		}
	}
	srv := httptest.NewServer(http.HandlerFunc(h))
	t.Cleanup(srv.Close)
	return srv
}

// TestIntegrationRestRoundTrip exercises create -> message -> cost -> delete and
// asserts the 201/202/200/204 status mapping is handled. Uses an httptest stub;
// the real-server variant runs via TestMain in Plan 06.
func TestIntegrationRestRoundTrip(t *testing.T) {
	srv := newRESTStub(t, "good", nil)
	c := AttachClient(srv.URL, "good")
	ctx := context.Background()

	id, err := c.CreateSession(ctx, ".")
	if err != nil {
		t.Fatalf("CreateSession: %v", err)
	}
	if id != "sess-1" {
		t.Fatalf("id = %q, want sess-1", id)
	}
	if err := c.PostMessage(ctx, id, "hi", ""); err != nil {
		t.Fatalf("PostMessage: %v", err)
	}
	cost, err := c.Cost(ctx, id)
	if err != nil {
		t.Fatalf("Cost: %v", err)
	}
	if cost.TotalUsd != 0.42 || cost.Turns != 1 {
		t.Fatalf("cost = %+v, want {0.42,1}", cost)
	}
	if err := c.DeleteSession(ctx, id); err != nil {
		t.Fatalf("DeleteSession: %v", err)
	}
}

// TestIntegration401 asserts a wrong bearer token yields *VossError{401}.
func TestIntegration401(t *testing.T) {
	srv := newRESTStub(t, "good", nil)
	c := AttachClient(srv.URL, "wrong")
	_, err := c.CreateSession(context.Background(), ".")
	var ve *VossError
	if !errors.As(err, &ve) {
		t.Fatalf("error %v is not *VossError", err)
	}
	if ve.Status != 401 {
		t.Fatalf("status = %d, want 401", ve.Status)
	}
}

// TestIntegration409 asserts a message posted while a turn is running surfaces
// as *VossError{409}. The stub returns 409 directly; the concurrent-goroutine
// variant against a real server runs via TestMain in Plan 06 (RESEARCH
// Pitfall 7).
func TestIntegration409(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusConflict)
		_, _ = io.WriteString(w, `{"v":1,"detail":"a turn is already running"}`)
	}))
	t.Cleanup(srv.Close)

	c := AttachClient(srv.URL, "good")
	err := c.PostMessage(context.Background(), "sess-1", "hi", "")
	var ve *VossError
	if !errors.As(err, &ve) {
		t.Fatalf("error %v is not *VossError", err)
	}
	if ve.Status != 409 {
		t.Fatalf("status = %d, want 409", ve.Status)
	}
}

// TestBearerHeader asserts every REST request carries Authorization: Bearer
// <token> via the single client chokepoint.
func TestBearerHeader(t *testing.T) {
	var last string
	srv := newRESTStub(t, "good", &last)
	c := AttachClient(srv.URL, "good")
	if _, err := c.CreateSession(context.Background(), "."); err != nil {
		t.Fatalf("CreateSession: %v", err)
	}
	if last != "Bearer good" {
		t.Fatalf("Authorization = %q, want %q", last, "Bearer good")
	}
}

// TestPermissionAllow will assert PermissionReply with an allow choice maps to
// status "ok". RED until Plan 06 (V13.3-06) per CONTEXT D-09 (route-contract
// half is automated).
func TestPermissionAllow(t *testing.T) {
	// TODO(V13.3-06): assert PermissionReply(...,"a") -> ok (Stale=false).
	t.Skip("RED: PermissionReply implemented in Plan 06 (V13.3-06)")
}

// TestPermissionDeny will assert PermissionReply with a deny choice maps to
// status "ok"/denied, and a stale id maps to Stale=true. RED until Plan 06.
func TestPermissionDeny(t *testing.T) {
	// TODO(V13.3-06): assert PermissionReply(...,"d") and the stale-id path.
	t.Skip("RED: PermissionReply implemented in Plan 06 (V13.3-06)")
}
