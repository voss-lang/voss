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
		userBlock("hi"),
		roleBlock("plan", "(empty plan)"),
		{kind: blockAssistant, text: "hello from fake turn", footer: "assistant · $0.0000 · conf 0.90", joined: true},
		assistantBlock("echo: hi"),
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("blocks = %+v, want %+v", got, want)
	}
	if st.busy || st.streaming != "" || st.thinking != "" {
		t.Fatalf("state after idle = %+v, want idle and empty", st)
	}
}

// Expected text is copied from voss/harness/tui/renderer.py.
func TestReduceSingleEvents(t *testing.T) {
	budget := 6000
	truncated := []string{"AGENTS.md", "VOSS.md"}
	plans := 2
	steps := []voss.PlanStep{{Name: "fs_read"}, {Name: "fs_edit"}}
	tool := func(text string) []block { return []block{{kind: blockTool, text: text, joined: true}} }
	for _, tc := range []struct {
		name string
		ev   voss.TypedEvent
		want []block
	}{
		{"pending tool waits for its result", voss.ToolEvent{Name: "fs_read", State: "pending"}, nil},
		{"finished tool is one row", voss.ToolEvent{Name: "fs_read", State: "ok", Summary: str("12 lines")}, tool("fs_read ✓ 12 lines")},
		{"failed tool", voss.ToolEvent{Name: "fs_edit", State: "error"}, tool("fs_edit ✗")},
		{"multi-line tool summary keeps its first line", voss.ToolEvent{Name: "fs_read", State: "ok", Summary: str("2cf24dba│hello\nabc│world")}, tool("fs_read ✓ 2cf24dba│hello")},
		{"plan lists its steps", voss.PlanEvent{Steps: &steps}, []block{roleBlock("plan", "  · fs_read\n  · fs_edit")}},
		{"stepless plan", voss.PlanEvent{}, []block{roleBlock("plan", "(empty plan)")}},
		{"clarify with its confidence bar", voss.ClarifyEvent{Question: "which file?", Confidence: 0.4}, []block{roleBlock("clarify", "which file?"), {kind: blockConfidence, conf: float64(float32(0.4)), joined: true}}},
		{"warning", voss.WarningEvent{Message: "cognition error"}, []block{roleBlock("warning", "⚠ cognition error")}},
		{"cognition loaded", voss.CognitionLoaded{ArchitectureTokens: 1234, ConstraintsCount: 3, PlansLoaded: &plans}, []block{roleBlock("cognition", "cognition: architecture (1.2k) + 3 constraints + 2 plans + 0 decisions")}},
		{"architecture over budget", voss.CognitionOverflow{ArchitectureTokens: 7000, Budget: &budget}, []block{roleBlock("warning", "⚠ architecture.md is 7000 tokens (over 6000 budget) — /analyze can rewrite a tighter digest")}},
		{"principles over budget", voss.PrinciplesOverflow{PrinciplesTokens: 1200}, []block{roleBlock("warning", "⚠ principles block is 1200 tokens (over 1000 budget) — truncated")}},
		{"instructions truncated", voss.InstructionsOverflow{InstructionsTokens: 5000, Truncated: &truncated}, []block{roleBlock("warning", "⚠ instruction files truncated to 4000 tokens (AGENTS.md, VOSS.md)")}},
		{"newer server event is visible", voss.UnknownEvent{Type: "tool.progress"}, []block{roleBlock("notice", `unsupported event "tool.progress" from a newer server`)}},
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

func TestServerErrorStreamKeepsItsRoleInTheFooter(t *testing.T) {
	st, _ := reduce(turn{busy: true}, voss.StreamDelta{Text: "\n[error: provider 400]\n"})
	st, got := reduce(st, voss.StreamFinalize{Role: "system"})
	want := []block{{kind: blockAssistant, text: "\n[error: provider 400]\n", footer: "system", joined: true}}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("blocks = %+v, want %+v", got, want)
	}
	if st.streaming != "" {
		t.Fatalf("streaming = %q after finalize", st.streaming)
	}
}

func TestInterruptedStreamSaysSoInItsFooter(t *testing.T) {
	st, _ := reduce(turn{busy: true, interrupted: true}, voss.StreamDelta{Text: "partial"})
	st, got := reduce(st, voss.StreamFinalize{Role: "assistant"})
	if len(got) != 1 || got[0].footer != "assistant · interrupted" || st.interrupted {
		t.Fatalf("blocks = %+v, interrupted left %v", got, st.interrupted)
	}
}

func TestIdleWithoutFinalizeFlushesPartialAndDropsPrompt(t *testing.T) {
	st := turn{busy: true, thinking: "planning", permission: &voss.PermissionUpdated{Id: "p1"}}
	st, _ = reduce(st, voss.StreamDelta{Text: "half"})
	st, got := reduce(st, voss.SessionIdle{})
	if want := []block{{kind: blockAssistant, text: "half", joined: true}}; !reflect.DeepEqual(got, want) {
		t.Fatalf("blocks = %+v, want %+v", got, want)
	}
	if st.busy || st.permission != nil {
		t.Fatalf("state after idle = %+v", st)
	}
	if st.thinking != "planning" {
		t.Fatalf("thinking = %q; Textual keeps the thinking toast until a final answer", st.thinking)
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

func TestLastFinishedToolIsKeptForCtrlO(t *testing.T) {
	st, _ := reduce(turn{}, voss.ToolEvent{Name: "fs_read", State: "ok"})
	st, _ = reduce(st, voss.ToolEvent{Name: "fs_edit", State: "pending"})
	if st.lastTool == nil || st.lastTool.Name != "fs_read" {
		t.Fatalf("lastTool = %+v, want the finished fs_read, not the pending call", st.lastTool)
	}
}

func TestFinalAnswerClearsTheThinkingToast(t *testing.T) {
	st, _ := reduce(turn{busy: true}, voss.ThinkingEvent{Label: "planning 1/1"})
	if st.thinking != "planning 1/1" {
		t.Fatalf("thinking = %q", st.thinking)
	}
	st, _ = reduce(st, voss.FinalEvent{Text: "done"})
	if st.thinking != "" {
		t.Fatalf("thinking = %q after final", st.thinking)
	}
}
