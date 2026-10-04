package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
	voss "github.com/vosslang/voss/sdk/go"
)

func TestResumeArgs(t *testing.T) {
	dir := t.TempDir()
	for _, args := range [][]string{
		{"resume", "saved name", "--cwd", dir},
		{"resume", "--cwd", dir, "saved name"},
		{"--cwd", dir, "resume", "saved name"},
	} {
		o, err := parseArgs(args)
		if err != nil || o.cmd != "resume" || o.resume != "saved name" || o.cwd != dir {
			t.Fatalf("parseArgs(%v) = %+v, %v", args, o, err)
		}
	}
	for _, args := range [][]string{{"resume"}, {"resume", "one", "two"}} {
		if _, err := parseArgs(args); err == nil {
			t.Fatalf("accepted %v", args)
		}
	}
}

func resumeServer(t *testing.T) (*fakeServer, *voss.Client) {
	t.Helper()
	f := &fakeServer{}
	cwd := t.TempDir()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/sessions/saved":
			_ = json.NewEncoder(w).Encode(map[string]any{"sessions": []voss.SavedSession{
				{Id: "sess-1", Name: "current"}, {Id: "saved", Name: "previous session"},
			}})
		case strings.HasSuffix(r.URL.Path, "/events"):
			w.Header().Set("Content-Type", "text/event-stream")
			w.(http.Flusher).Flush()
			<-r.Context().Done()
		case r.Method == http.MethodGet:
			_ = json.NewEncoder(w).Encode(voss.SessionInfo{Id: "saved", Cwd: cwd, Model: "saved-model"})
		default:
			var body map[string]any
			_ = json.NewDecoder(r.Body).Decode(&body)
			f.mu.Lock()
			f.reqs = append(f.reqs, request{r.URL.Path, body})
			f.mu.Unlock()
			if r.URL.Path == "/session" {
				if body["resume"] == "missing" {
					w.WriteHeader(http.StatusNotFound)
					_, _ = w.Write([]byte(`{"detail":"no saved session"}`))
					return
				}
				w.WriteHeader(http.StatusCreated)
				_, _ = w.Write([]byte(`{"id":"saved","auth":"codex-oauth","resumed":true}`))
			} else {
				w.WriteHeader(http.StatusAccepted)
			}
		}
	}))
	t.Cleanup(srv.Close)
	return f, voss.AttachClient(srv.URL, "test")
}

func TestResumeOpensSavedContextAndCancelsStream(t *testing.T) {
	f, client := resumeServer(t)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	conn, err := openChatSession(ctx, client, options{cwd: t.TempDir(), resume: "saved name"})
	if err != nil {
		t.Fatal(err)
	}
	conn.cancel()
	if msg := waitEvent(conn.events)().(sessionEventMsg); msg.ev != nil {
		t.Fatalf("stream remained open: %+v", msg)
	}
	requests := f.requestsTo("/session")
	if len(requests) != 1 || requests[0].body["resume"] != "saved name" || conn.meta.ID != "saved" || conn.meta.Model != "saved-model" {
		t.Fatalf("resume = %+v, meta = %+v", requests, conn.meta)
	}
}

func TestQueuedResumeSwitchesBeforeSendingAndIgnoresOldStream(t *testing.T) {
	f, client := resumeServer(t)
	old := make(chan voss.TypedEvent)
	d := newDriver(t, client, old)
	cancelled := false
	d.m.cancelStream = func() { cancelled = true; close(old) }
	t.Cleanup(func() { d.m.cancelStream() })
	d.m.turn.busy = true
	d.m.mode = "edit"
	d.m.lastResponse = "old answer"
	d.m.queue = []string{"/resume saved", "what did we decide?"}
	d.send(eventMsg{voss.SessionIdle{}})
	d.until("resumed message", func() bool { return len(f.requestsTo("/message")) == 1 })
	if !cancelled || d.m.sessionID != "saved" || d.m.lastResponse != "" {
		t.Fatalf("old session not cleared: id=%s cancelled=%v", d.m.sessionID, cancelled)
	}
	sent := f.requestsTo("/message")[0]
	if sent.path != "/session/saved/message" || text(sent) != "what did we decide?" || sent.body["mode"] != "edit" {
		t.Fatalf("queued message = %+v", sent)
	}
	d.send(sessionEventMsg{events: old, ev: voss.FinalEvent{Text: "stale"}})
	d.send(sessionEventMsg{events: old})
	if d.m.offline || d.m.lastResponse == "stale" || !d.m.turn.busy {
		t.Fatal("old stream changed the resumed session")
	}
}

func TestFailedResumeKeepsSessionAndRestoresQueuedInput(t *testing.T) {
	f, client := resumeServer(t)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, client, events)
	d.m.turn.busy = true
	d.m.queue = []string{"/resume missing", "follow up"}
	d.send(eventMsg{voss.SessionIdle{}})
	d.until("resume failure", func() bool { return strings.Contains(d.transcript(), "no saved session") })
	if d.m.sessionID != "sess-1" || len(f.requestsTo("/message")) != 0 || !strings.Contains(d.m.editor.Value(), "follow up") || len(d.m.queue) != 0 {
		t.Fatal("failed resume sent queued input or discarded the active session")
	}
}

func TestResumePickerFiltersAndSelectsSavedSession(t *testing.T) {
	_, client := resumeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)
	d.m.cancelStream = func() { close(events) }
	t.Cleanup(func() { d.m.cancelStream() })
	d.typeText("/resume")
	d.press("enter")
	d.until("session picker", func() bool { return d.m.pal.kind == paletteSession })
	if len(d.m.pal.names) != 1 || d.m.pal.names[0] != "saved" {
		t.Fatalf("picker includes current session: %+v", d.m.pal)
	}
	d.typeText("no match")
	d.press("enter")
	if d.m.pal.kind != paletteSession || len(d.m.pal.names) != 0 {
		t.Fatal("empty picker submitted a prompt")
	}
	d.m.editor.Reset()
	d.send(tea.KeyPressMsg{Code: 'p', Text: "previous"})
	d.press("enter")
	d.until("selected session", func() bool { return d.m.sessionID == "saved" })
}
