package voss

import "testing"

// TestVossError lives in errors_test.go (Plan 02 implemented errors.go).

// TestBearerHeader will assert every REST method attaches
// "Authorization: Bearer <token>" via a recording httptest server. RED until
// Plan 03 (V13.3-03) lands rest.go.
func TestBearerHeader(t *testing.T) {
	// TODO(V13.3-03): drive a *Client (AttachClient) against an httptest server
	// and assert the bearer header is present on every request, including SSE.
	t.Skip("RED: rest.go bearer injection implemented in Plan 03 (V13.3-03)")
}

// TestIntegrationRestRoundTrip will exercise create -> message -> cost ->
// delete against a real `voss serve` (VOSS_SERVE_FAKE_TURN) and assert the
// 201/202/200/204 status mapping. RED until Plan 03/06.
func TestIntegrationRestRoundTrip(t *testing.T) {
	// TODO(V13.3-03/06): full REST round-trip against the shared TestMain server.
	t.Skip("RED: REST client + integration harness implemented in Plan 03/06")
}

// TestIntegration401 will assert a wrong/absent bearer token yields a typed
// VossError with Status 401. RED until Plan 03/06.
func TestIntegration401(t *testing.T) {
	// TODO(V13.3-03/06): post with a bad token, assert *VossError{Status:401}.
	t.Skip("RED: 401 handling implemented in Plan 03/06")
}

// TestIntegration409 will assert posting a second message while a turn is
// running returns a typed VossError with Status 409. RED until Plan 03/06.
func TestIntegration409(t *testing.T) {
	// TODO(V13.3-03/06): fire two concurrent posts (sync.WaitGroup), assert one
	// returns *VossError{Status:409} (RESEARCH Pitfall 7).
	t.Skip("RED: 409 busy handling implemented in Plan 03/06")
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
