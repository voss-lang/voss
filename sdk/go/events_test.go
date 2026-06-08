package voss

import "testing"

// allEventTypes is the authoritative 21-member set of AgentEvent `type` strings
// from voss/harness/server/events.py. Plan 02's Decode() must dispatch every
// one of these to its typed Go value, and any other value to ErrUnknownEventType.
// Note: principles_overflow is in events.py but NOT in PROTOCOL.md (RESEARCH
// Pitfall 4) — it MUST be covered.
var allEventTypes = []string{
	"server.connected",
	"session.idle",
	"permission.updated",
	"banner",
	"user",
	"thinking",
	"plan",
	"tool",
	"clarify",
	"final",
	"stream.delta",
	"stream.finalize",
	"status",
	"cognition_loaded",
	"cognition_overflow",
	"principles_overflow",
	"warning",
	"probable",
	"budget.updated",
	"confidence.updated",
	"gate.updated",
}

// TestDecodeAllMembers will assert that Decode() turns an EventEnvelope for each
// of the 21 type strings into the corresponding typed Go struct carrying its
// fields (no silent drop). RED until Plan 02 (V13.3-02) lands events.go.
func TestDecodeAllMembers(t *testing.T) {
	if len(allEventTypes) != 21 {
		t.Fatalf("decode table has %d entries, want 21", len(allEventTypes))
	}
	// TODO(V13.3-02): for each type in allEventTypes, build an EventEnvelope and
	// assert Decode(env) returns the matching TypedEvent with populated fields.
	t.Skip("RED: Decode() implemented in Plan 02 (V13.3-02)")
}

// TestDecodeUnknownType will assert that an unrecognized `type` yields a typed
// ErrUnknownEventType (matchable via errors.As) and never a nil event with a
// nil error. RED until Plan 02 (V13.3-02).
func TestDecodeUnknownType(t *testing.T) {
	// TODO(V13.3-02): Decode an envelope with type "does.not.exist" and assert
	// errors.As(err, &ErrUnknownEventType{}) with Type == "does.not.exist".
	t.Skip("RED: Decode()/ErrUnknownEventType implemented in Plan 02 (V13.3-02)")
}
