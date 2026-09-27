package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"reflect"
	"testing"

	voss "github.com/vosslang/voss/sdk/go"
)

func str(s string) *string { return &s }

// replayCapture serves a recorded SSE stream through the SDK so the reducer
// sees exactly what the SDK decodes from the wire.
func replayCapture(t *testing.T, path string) []voss.TypedEvent {
	t.Helper()
	body, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = w.Write(body)
	}))
	defer srv.Close()
	ch, err := voss.AttachClient(srv.URL, "t").Events(context.Background(), "SESSION")
	if err != nil {
		t.Fatal(err)
	}
	var evs []voss.TypedEvent
	for ev := range ch {
		evs = append(evs, ev)
	}
	return evs
}

func TestFakeTurnCaptureCommitsUserStreamAndFinal(t *testing.T) {
	evs := replayCapture(t, "testdata/fake_turn.sse")
	if len(evs) != 9 {
		t.Fatalf("decoded %d events from the capture, want 9", len(evs))
	}
	var st turn
	var got []block
	for _, ev := range evs {
		var out []block
		st, out = reduce(st, ev)
		got = append(got, out...)
	}
	want := []block{
		{blockUser, "hi"},
		{blockAssistant, "hello from fake turn"},
		{blockAssistant, "echo: hi"},
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("blocks = %+v, want %+v", got, want)
	}
	if st.busy || st.streaming != "" || st.thinking != "" {
		t.Fatalf("state after idle = %+v, want idle and empty", st)
	}
}

func TestReduceSingleEvents(t *testing.T) {
	steps := []voss.PlanStep{{Name: "fs_read"}, {Name: "fs_edit"}}
	for _, tc := range []struct {
		name string
		ev   voss.TypedEvent
		want []block
	}{
		{"pending tool waits for its result", voss.ToolEvent{Name: "fs_read", State: "pending"}, nil},
		{"finished tool is one row", voss.ToolEvent{Name: "fs_read", State: "ok", Summary: str("12 lines")}, []block{{blockTool, "fs_read ✓ 12 lines"}}},
		{"failed tool", voss.ToolEvent{Name: "fs_edit", State: "error"}, []block{{blockTool, "fs_edit ✗"}}},
		{"plan lists its steps", voss.PlanEvent{Steps: &steps}, []block{{blockPlan, "plan: fs_read, fs_edit"}}},
		{"stepless plan is hidden", voss.PlanEvent{}, nil},
		{"clarify", voss.ClarifyEvent{Question: "which file?"}, []block{{blockClarify, "which file?"}}},
		{"warning", voss.WarningEvent{Message: "cognition error"}, []block{{blockWarning, "cognition error"}}},
		{"newer server event is visible", voss.UnknownEvent{Type: "tool.progress"}, []block{{blockNotice, `unsupported event "tool.progress" from a newer server`}}},
		{"swarm events are ignored for now", voss.SwarmComplete{}, nil},
	} {
		t.Run(tc.name, func(t *testing.T) {
			_, got := reduce(turn{}, tc.ev)
			if !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("blocks = %+v, want %+v", got, tc.want)
			}
		})
	}
}

func TestServerErrorStreamCommitsAsError(t *testing.T) {
	st, _ := reduce(turn{busy: true}, voss.StreamDelta{Text: "\n[error: provider 400]\n"})
	st, got := reduce(st, voss.StreamFinalize{Role: "system"})
	if want := []block{{blockError, "[error: provider 400]"}}; !reflect.DeepEqual(got, want) {
		t.Fatalf("blocks = %+v, want %+v", got, want)
	}
	if st.streaming != "" {
		t.Fatalf("streaming = %q after finalize", st.streaming)
	}
}

func TestIdleWithoutFinalizeFlushesPartialAndDropsPrompt(t *testing.T) {
	st := turn{busy: true, thinking: "planning", permission: &voss.PermissionUpdated{Id: "p1"}}
	st, _ = reduce(st, voss.StreamDelta{Text: "half"})
	st, got := reduce(st, voss.SessionIdle{})
	if want := []block{{blockAssistant, "half"}}; !reflect.DeepEqual(got, want) {
		t.Fatalf("blocks = %+v, want %+v", got, want)
	}
	if st.busy || st.permission != nil || st.thinking != "" {
		t.Fatalf("state after idle = %+v", st)
	}
	st, _ = reduce(st, voss.StreamDelta{Text: "next"})
	if st.streaming != "next" {
		t.Fatalf("next turn inherited text: %q", st.streaming)
	}
}

func TestStatusUpdatesFooterState(t *testing.T) {
	st, _ := reduce(turn{model: "—"}, voss.StatusEvent{Model: "claude-sonnet", Tokens: 1234, CostUsd: 0.05, CtxPct: 0.3})
	if st.model != "claude-sonnet" || st.tokens != 1234 || st.costUSD < 0.0499 || st.ctxPct < 0.299 {
		t.Fatalf("state = %+v", st)
	}
	st, _ = reduce(st, voss.StatusEvent{Tokens: 1})
	if st.model != "claude-sonnet" {
		t.Fatalf("empty model overwrote %q", st.model)
	}
}

func TestPermissionEventOpensPrompt(t *testing.T) {
	st, _ := reduce(turn{busy: true}, voss.PermissionUpdated{Id: "p1", ToolName: "fs_edit"})
	if st.permission == nil || st.permission.Id != "p1" {
		t.Fatalf("permission = %+v", st.permission)
	}
}
