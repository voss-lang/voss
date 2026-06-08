package voss

import "testing"

// TestAttachRoundTrip will assert AttachClient(baseURL, token) builds a client
// that owns no child process and round-trips against a running server. RED
// until Plan 05 (V13.3-05) lands the attach/spawn constructors.
func TestAttachRoundTrip(t *testing.T) {
	// TODO(V13.3-05): AttachClient against the shared TestMain server, assert a
	// REST call succeeds and Close() does not kill the externally-owned server.
	t.Skip("RED: AttachClient implemented in Plan 05 (V13.3-05)")
}

// TestSpawnNoOrphan will assert Spawn() launches `voss serve`, and Close()
// kills + reaps it leaving no orphan (kill(pid,0) -> ESRCH). RED until Plan 05.
func TestSpawnNoOrphan(t *testing.T) {
	// TODO(V13.3-05): Spawn with VOSS_SERVE_FAKE_TURN, capture pid, Close(),
	// assert the process is gone (no orphan; stdin-EOF + Kill()+Wait()).
	t.Skip("RED: Spawn no-orphan implemented in Plan 05 (V13.3-05)")
}

// TestSpawnBadInterpreter will assert Spawn() with an invalid interpreter
// returns a typed SpawnError rather than hanging. RED until Plan 05.
func TestSpawnBadInterpreter(t *testing.T) {
	// TODO(V13.3-05): set VOSS_PYTHON to a nonexistent path, assert Spawn returns
	// a *SpawnError promptly (no handshake hang).
	t.Skip("RED: SpawnError handling implemented in Plan 05 (V13.3-05)")
}

// TestNoFFI will assert the SDK introduces no cgo/FFI and no orchestration
// reimplementation (SPEC req 7 / VSDK-GO-07). RED until Plan 06 (V13.3-06)
// owns the enforced grep guard.
func TestNoFFI(t *testing.T) {
	// TODO(V13.3-06): walk sdk/go and assert no cgo import and no import of
	// orchestration-internal packages.
	t.Skip("RED: no-FFI/no-reimpl guard enforced in Plan 06 (V13.3-06)")
}
