package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

func modelServer(t *testing.T) (*fakeServer, *voss.Client) {
	t.Helper()
	f := &fakeServer{}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/models" {
			_ = json.NewEncoder(w).Encode(voss.ModelCatalog{Models: []voss.ModelChoice{
				{Id: "claude-opus-5-5", Name: "Claude Opus 5.5", Provider: "anthropic", ProviderLabel: "Claude subscription", Auth: "claude", Connected: true},
				{Id: "gpt-6.1-sol", Name: "GPT 6.1 Sol", Provider: "openai", ProviderLabel: "Codex subscription", Auth: "codex", Connected: true},
				{Id: "gpt-6.1-sol", Name: "GPT 6.1 Sol", Provider: "openai", ProviderLabel: "OpenAI API", Auth: "api"},
			}})
			return
		}
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		f.mu.Lock()
		f.reqs = append(f.reqs, request{r.URL.Path, body})
		f.mu.Unlock()
		if strings.HasSuffix(r.URL.Path, "/model") {
			if body["model"] == "missing" {
				w.WriteHeader(http.StatusBadRequest)
				_, _ = w.Write([]byte(`{"detail":"No matching model"}`))
				return
			}
			info := voss.SessionInfo{Id: "sess-1", Model: "gpt-6.1-sol", Provider: "Codex", Auth: "codex-oauth"}
			if body["auth"] == "claude" {
				info.Model, info.Provider, info.Auth = "claude-sonnet-5-5", "Anthropic", "claude-agent"
			}
			_ = json.NewEncoder(w).Encode(info)
			return
		}
		w.WriteHeader(http.StatusAccepted)
	}))
	t.Cleanup(srv.Close)
	return f, voss.AttachClient(srv.URL, "test")
}

func TestModelPickerFiltersSelectsAndUpdatesFooter(t *testing.T) {
	f, client := modelServer(t)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, client, events)
	d.send(windowSize(120, 36))
	d.typeText("/models")
	d.press("enter")
	d.until("model picker", func() bool { return d.m.pal.kind == paletteModel })
	if len(d.m.pal.names) != 3 || !strings.Contains(ansi.Strip(d.m.bottom()), "login required") {
		t.Fatalf("picker = %+v", d.m.pal)
	}
	d.typeText("no match")
	d.press("enter")
	if d.m.pal.kind != paletteModel || len(d.m.pal.names) != 0 || len(f.requestsTo("/message")) != 0 {
		t.Fatal("empty picker submitted a message")
	}
	d.m.editor.Reset()
	d.typeText("codex")
	d.press("enter")
	d.until("model selected", func() bool { return d.m.turn.model == "gpt-6.1-sol" })
	requests := f.requestsTo("/model")
	if len(requests) != 1 || requests[0].body["auth"] != "codex" || requests[0].body["provider"] != "openai" {
		t.Fatalf("selection = %+v", requests)
	}
	if d.m.provider != "Codex" || d.m.auth != "codex-oauth" || !strings.Contains(ansi.Strip(d.m.bottom()), "gpt-6.1-sol") {
		t.Fatalf("footer = %s", ansi.Strip(d.m.bottom()))
	}
	d.typeText("/auth")
	d.press("enter")
	d.until("auth picker", func() bool { return d.m.pal.kind == paletteAuth })
	d.typeText("claude")
	d.press("enter")
	d.until("claude selected", func() bool { return d.m.auth == "claude-agent" })
	if d.m.turn.model != "claude-sonnet-5-5" {
		t.Fatal("auth switch kept an incompatible model")
	}
}

func TestQueuedModelSwitchFinishesBeforeNextMessage(t *testing.T) {
	f, client := modelServer(t)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, client, events)
	d.m.turn.busy = true
	d.m.queue = []string{"/model gpt-6.1-sol", "hello"}
	d.send(eventMsg{voss.SessionIdle{}})
	if !d.m.selecting || len(d.m.queue) != 1 {
		t.Fatal("queue continued while model switch was pending")
	}
	d.until("next turn", func() bool { return len(f.requestsTo("/message")) == 1 })
	if d.m.turn.model != "gpt-6.1-sol" || d.m.auth != "codex-oauth" || text(f.requestsTo("/message")[0]) != "hello" {
		t.Fatal("next turn used stale selection")
	}
}

func TestFailedModelSwitchRestoresQueueAndKeepsSelection(t *testing.T) {
	f, client := modelServer(t)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, client, events)
	d.m.turn.model, d.m.provider, d.m.auth = "old-model", "Anthropic", "claude-agent"
	d.m.turn.busy = true
	d.m.queue = []string{"/model missing", "follow up"}
	d.send(eventMsg{voss.SessionIdle{}})
	d.typeText("draft")
	d.until("switch failure", func() bool { return strings.Contains(d.transcript(), "No matching model") })
	if d.m.turn.model != "old-model" || d.m.provider != "Anthropic" || d.m.auth != "claude-agent" || d.m.selecting {
		t.Fatal("failed switch changed active selection")
	}
	if d.m.editor.Value() != "follow up\ndraft" || len(f.requestsTo("/message")) != 0 || len(d.m.queue) != 0 {
		t.Fatalf("pending input = %q", d.m.editor.Value())
	}
}

func TestCancelModelPickerRestoresPendingPrompt(t *testing.T) {
	f, client := modelServer(t)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, client, events)
	d.m.turn.busy = true
	d.m.queue = []string{"/models", "follow up"}
	d.send(eventMsg{voss.SessionIdle{}})
	d.until("picker", func() bool { return d.m.pal.kind == paletteModel })
	d.typeText("gpt")
	d.press("esc")
	if d.m.pal.kind != paletteNone || d.m.editor.Value() != "follow up" || len(f.requestsTo("/model")) != 0 || len(f.requestsTo("/message")) != 0 {
		t.Fatal("cancelled picker lost or submitted pending input")
	}
}

func TestStaleModelResponseCannotChangeResumedSession(t *testing.T) {
	m := newChatModel(nil, nil, sessionMeta{ID: "new", Model: "current", Auth: "claude-agent"}, nil)
	next, _ := m.Update(modelSelectedMsg{id: "old", info: voss.SessionInfo{Model: "stale"}})
	if next.(chatModel).turn.model != "current" {
		t.Fatal("stale response replaced resumed selection")
	}
}

func TestAuthFlag(t *testing.T) {
	o, err := parseArgs([]string{"--auth", "codex"})
	if err != nil || o.auth != "codex" {
		t.Fatalf("auth = %q, %v", o.auth, err)
	}
}

func TestCatalogFailureRestoresPendingInput(t *testing.T) {
	m := newChatModel(nil, nil, sessionMeta{ID: "current", Model: "old-model"}, nil)
	m.selecting = true
	m.queue = []string{"pending prompt"}
	next, _ := m.Update(modelListMsg{id: "current", err: errors.New("unavailable")})
	got := next.(chatModel)
	if got.selecting || got.editor.Value() != "pending prompt" || got.turn.model != "old-model" || len(got.queue) != 0 {
		t.Fatal("catalog failure changed selection or discarded queued input")
	}
}
