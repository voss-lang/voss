package voss

import (
	"encoding/json"
	"errors"
	"testing"
)

// allEventTypes is the authoritative 21-member set of AgentEvent `type` strings
// from voss/harness/server/events.py. Decode() must dispatch every one to its
// typed Go value, and any other value to ErrUnknownEventType. Note:
// principles_overflow is in events.py but NOT in PROTOCOL.md (RESEARCH
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

// envFromEvent builds an EventEnvelope wrapping the given raw event JSON via the
// generated EventEnvelope_Event union (its UnmarshalJSON stores the raw bytes).
func envFromEvent(t *testing.T, eventJSON string) EventEnvelope {
	t.Helper()
	var u EventEnvelope_Event
	if err := json.Unmarshal([]byte(eventJSON), &u); err != nil {
		t.Fatalf("unmarshal event %q: %v", eventJSON, err)
	}
	return EventEnvelope{Event: u}
}

// decodeCase is one row of the 21-member decode table: a fixture JSON for a
// `type` plus an assertion that Decode produced the right typed value.
type decodeCase struct {
	typ   string
	json  string
	check func(t *testing.T, ev TypedEvent)
}

func decodeTable() []decodeCase {
	return []decodeCase{
		{"server.connected", `{"v":1,"type":"server.connected"}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(ServerConnected); !ok {
				t.Fatalf("got %T, want ServerConnected", ev)
			}
		}},
		{"session.idle", `{"v":1,"type":"session.idle","session_id":"sess-1"}`, func(t *testing.T, ev TypedEvent) {
			e, ok := ev.(SessionIdle)
			if !ok {
				t.Fatalf("got %T, want SessionIdle", ev)
			}
			if e.SessionId != "sess-1" {
				t.Fatalf("SessionId = %q, want sess-1", e.SessionId)
			}
		}},
		{"permission.updated", `{"v":1,"type":"permission.updated","id":"ab12","tool_name":"fs_edit","args":{"path":"x"},"dimension":"tool"}`, func(t *testing.T, ev TypedEvent) {
			e, ok := ev.(PermissionUpdated)
			if !ok {
				t.Fatalf("got %T, want PermissionUpdated", ev)
			}
			if e.Id != "ab12" || e.ToolName != "fs_edit" {
				t.Fatalf("id/tool_name = %q/%q, want ab12/fs_edit", e.Id, e.ToolName)
			}
			if e.Args == nil || (*e.Args)["path"] != "x" {
				t.Fatalf("args not populated: %+v", e.Args)
			}
			if e.Dimension == nil || *e.Dimension != "tool" {
				t.Fatalf("dimension not populated: %+v", e.Dimension)
			}
		}},
		{"banner", `{"v":1,"type":"banner","model":"m","cwd":"/x","git":"main"}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(BannerEvent); !ok {
				t.Fatalf("got %T, want BannerEvent", ev)
			}
		}},
		{"user", `{"v":1,"type":"user","task":"do it"}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(UserEvent); !ok {
				t.Fatalf("got %T, want UserEvent", ev)
			}
		}},
		{"thinking", `{"v":1,"type":"thinking","label":"planning"}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(ThinkingEvent); !ok {
				t.Fatalf("got %T, want ThinkingEvent", ev)
			}
		}},
		{"plan", `{"v":1,"type":"plan","confidence":0.9,"steps":[],"cost_usd":0.0}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(PlanEvent); !ok {
				t.Fatalf("got %T, want PlanEvent", ev)
			}
		}},
		{"tool", `{"v":1,"type":"tool","name":"shell","args":{},"summary":"ran","state":"ok"}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(ToolEvent); !ok {
				t.Fatalf("got %T, want ToolEvent", ev)
			}
		}},
		{"clarify", `{"v":1,"type":"clarify","question":"which?","confidence":0.5}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(ClarifyEvent); !ok {
				t.Fatalf("got %T, want ClarifyEvent", ev)
			}
		}},
		{"final", `{"v":1,"type":"final","text":"done","confidence":0.8,"cost_usd":0.42}`, func(t *testing.T, ev TypedEvent) {
			e, ok := ev.(FinalEvent)
			if !ok {
				t.Fatalf("got %T, want FinalEvent", ev)
			}
			if e.Text != "done" || e.Confidence != 0.8 || e.CostUsd != 0.42 {
				t.Fatalf("final fields = %q/%v/%v, want done/0.8/0.42", e.Text, e.Confidence, e.CostUsd)
			}
		}},
		{"stream.delta", `{"v":1,"type":"stream.delta","text":"hi"}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(StreamDelta); !ok {
				t.Fatalf("got %T, want StreamDelta", ev)
			}
		}},
		{"stream.finalize", `{"v":1,"type":"stream.finalize","role":"assistant","confidence":0.9,"cost_usd":0.0}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(StreamFinalize); !ok {
				t.Fatalf("got %T, want StreamFinalize", ev)
			}
		}},
		{"status", `{"v":1,"type":"status","model":"m","tokens":10,"cost_usd":0.1,"ctx_pct":0.2}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(StatusEvent); !ok {
				t.Fatalf("got %T, want StatusEvent", ev)
			}
		}},
		{"cognition_loaded", `{"v":1,"type":"cognition_loaded","architecture_tokens":100,"constraints_count":2,"plans_loaded":1,"decisions_loaded":3}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(CognitionLoaded); !ok {
				t.Fatalf("got %T, want CognitionLoaded", ev)
			}
		}},
		{"cognition_overflow", `{"v":1,"type":"cognition_overflow","architecture_tokens":9000,"budget":6000}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(CognitionOverflow); !ok {
				t.Fatalf("got %T, want CognitionOverflow", ev)
			}
		}},
		{"principles_overflow", `{"v":1,"type":"principles_overflow","principles_tokens":5000,"budget":4000}`, func(t *testing.T, ev TypedEvent) {
			e, ok := ev.(PrinciplesOverflow)
			if !ok {
				t.Fatalf("got %T, want PrinciplesOverflow", ev)
			}
			if e.PrinciplesTokens != 5000 {
				t.Fatalf("PrinciplesTokens = %d, want 5000", e.PrinciplesTokens)
			}
			if e.Budget == nil || *e.Budget != 4000 {
				t.Fatalf("Budget = %+v, want 4000", e.Budget)
			}
		}},
		{"warning", `{"v":1,"type":"warning","message":"careful"}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(WarningEvent); !ok {
				t.Fatalf("got %T, want WarningEvent", ev)
			}
		}},
		{"probable", `{"v":1,"type":"probable","text":"yes","probability":0.7,"alternatives":[{"text":"no","probability":0.3}]}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(ProbableEvent); !ok {
				t.Fatalf("got %T, want ProbableEvent", ev)
			}
		}},
		{"budget.updated", `{"v":1,"type":"budget.updated","session_id":"s","spent":10.0,"limit":100.0,"remaining":90.0,"unit":"usd"}`, func(t *testing.T, ev TypedEvent) {
			e, ok := ev.(BudgetUpdated)
			if !ok {
				t.Fatalf("got %T, want BudgetUpdated", ev)
			}
			if e.Spent != 10.0 || e.Limit != 100.0 || e.Remaining != 90.0 {
				t.Fatalf("budget fields = %v/%v/%v, want 10/100/90", e.Spent, e.Limit, e.Remaining)
			}
			if e.Unit == nil || *e.Unit != Usd {
				t.Fatalf("unit = %+v, want usd", e.Unit)
			}
		}},
		{"confidence.updated", `{"v":1,"type":"confidence.updated","session_id":"s","message_id":"m1","score":0.6}`, func(t *testing.T, ev TypedEvent) {
			if _, ok := ev.(ConfidenceUpdated); !ok {
				t.Fatalf("got %T, want ConfidenceUpdated", ev)
			}
		}},
		{"gate.updated", `{"v":1,"type":"gate.updated","session_id":"s","gate":"budget","decision":"allow"}`, func(t *testing.T, ev TypedEvent) {
			e, ok := ev.(GateUpdated)
			if !ok {
				t.Fatalf("got %T, want GateUpdated", ev)
			}
			if e.Gate != "budget" || e.Decision != "allow" {
				t.Fatalf("gate/decision = %q/%q, want budget/allow", e.Gate, e.Decision)
			}
		}},
	}
}

// TestDecodeAllMembers asserts Decode() turns an EventEnvelope for each of the
// 21 type strings into the matching typed Go struct with fields populated, with
// no entry skipped and eventType() round-tripping the discriminator.
func TestDecodeAllMembers(t *testing.T) {
	table := decodeTable()
	if len(table) != 21 {
		t.Fatalf("decode table has %d entries, want 21", len(table))
	}
	// Every member of the authoritative set must have a table row.
	covered := map[string]bool{}
	for _, c := range table {
		covered[c.typ] = true
	}
	for _, want := range allEventTypes {
		if !covered[want] {
			t.Fatalf("decode table missing member %q", want)
		}
	}

	for _, c := range table {
		t.Run(c.typ, func(t *testing.T) {
			ev, err := Decode(envFromEvent(t, c.json))
			if err != nil {
				t.Fatalf("Decode(%s) error: %v", c.typ, err)
			}
			if ev == nil {
				t.Fatalf("Decode(%s) returned nil event with nil error", c.typ)
			}
			if ev.eventType() != c.typ {
				t.Fatalf("eventType() = %q, want %q", ev.eventType(), c.typ)
			}
			c.check(t, ev)
		})
	}
}

// TestDecodeUnknownType asserts an unrecognized `type` yields a typed
// ErrUnknownEventType (matchable via errors.As) carrying the raw type, never a
// nil error with a nil event.
func TestDecodeUnknownType(t *testing.T) {
	ev, err := Decode(envFromEvent(t, `{"v":1,"type":"future.event.v2"}`))
	if ev != nil {
		t.Fatalf("expected nil event for unknown type, got %T", ev)
	}
	if err == nil {
		t.Fatal("expected ErrUnknownEventType, got nil error")
	}
	var unknown ErrUnknownEventType
	if !errors.As(err, &unknown) {
		t.Fatalf("error %v is not ErrUnknownEventType", err)
	}
	if unknown.Type != "future.event.v2" {
		t.Fatalf("ErrUnknownEventType.Type = %q, want future.event.v2", unknown.Type)
	}
}
