package voss

import (
	"encoding/json"
	"testing"
)

// TestDiscriminatorProbe is a passing diagnostic that RECORDS the empirical
// shape of the oapi-codegen-generated union accessors, resolving RESEARCH open
// question A1 for Plan 02's Decode() dispatcher.
//
// Verified conclusion (see V13.3-01-SUMMARY.md):
//   - The generated union type is EventEnvelope_Event (the `event` field of the
//     EventEnvelope wrapper), not EventEnvelope itself.
//   - It exposes `func (t EventEnvelope_Event) Discriminator() (string, error)`
//     — the method EXISTS and returns (string, error). No json.Unmarshal
//     fallback is needed; Plan 02's Decode() reads the type via Discriminator().
//   - Per-member `AsX()` accessors exist for all 21 members, returning
//     (X, error) (e.g. AsServerConnected, AsGateUpdated, AsPrinciplesOverflow).
//   - *EventEnvelope_Event implements UnmarshalJSON, so an event object can be
//     loaded with json.Unmarshal into the union value directly.
func TestDiscriminatorProbe(t *testing.T) {
	var ev EventEnvelope_Event
	if err := json.Unmarshal([]byte(`{"v":1,"type":"server.connected"}`), &ev); err != nil {
		t.Fatalf("unmarshal into EventEnvelope_Event: %v", err)
	}

	disc, err := ev.Discriminator()
	if err != nil {
		t.Fatalf("Discriminator() returned error: %v", err)
	}
	if disc != "server.connected" {
		t.Fatalf("Discriminator() = %q, want %q", disc, "server.connected")
	}
	t.Logf("RESOLVED A1: EventEnvelope_Event.Discriminator() (string, error) present; returned %q", disc)

	sc, err := ev.AsServerConnected()
	if err != nil {
		t.Fatalf("AsServerConnected() returned error: %v", err)
	}
	t.Logf("AsServerConnected() ok: type=%q v=%v", sc.Type, sc.V)

	// A second member with fields, to confirm typed payload extraction works.
	var gate EventEnvelope_Event
	if err := json.Unmarshal([]byte(`{"v":1,"type":"gate.updated","session_id":"s1","gate":"budget","decision":"allow"}`), &gate); err != nil {
		t.Fatalf("unmarshal gate.updated: %v", err)
	}
	gd, err := gate.AsGateUpdated()
	if err != nil {
		t.Fatalf("AsGateUpdated() returned error: %v", err)
	}
	if gd.Decision != "allow" || gd.Gate != "budget" || gd.SessionId != "s1" {
		t.Fatalf("AsGateUpdated() payload mismatch: %+v", gd)
	}
	t.Logf("AsGateUpdated() ok: gate=%q decision=%q session_id=%q", gd.Gate, gd.Decision, gd.SessionId)
}
