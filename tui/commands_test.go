package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	voss "github.com/vosslang/voss/sdk/go"
)

func TestCommandDiscoveryUpdatesOpenPaletteWithoutBlockingInput(t *testing.T) {
	release := make(chan struct{}, 1)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/commands" {
			t.Errorf("unexpected request: %s", r.URL.Path)
		}
		<-release
		_, _ = w.Write([]byte(`{"commands":[{"name":"/skills","description":"list skills"},{"name":"/help","description":"remote override"},{"name":"/quit","description":"remote alias"}]}`))
	}))
	defer srv.Close()
	defer close(release)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, voss.AttachClient(srv.URL, "test"), events)
	d.typeText("/help")
	d.press("enter")
	if !strings.Contains(d.transcript(), "show this list") {
		t.Fatal("local help blocked on command discovery")
	}
	d.typeText("/sk")
	release <- struct{}{}
	d.until("discovered command", func() bool { return len(d.m.serverCommands) > 0 })
	if d.m.pal.kind != paletteSlash || len(d.m.pal.names) != 1 || d.m.pal.names[0] != "/skills" {
		t.Fatalf("palette did not refresh: %+v", d.m.pal)
	}
	if help := d.m.helpText(); !strings.Contains(help, "list skills") || strings.Contains(help, "remote override") || strings.Contains(help, "remote alias") {
		t.Fatalf("remote commands replaced local help: %s", help)
	}
	if command, ok := d.m.lookupCommand("/quit"); !ok || command.name != "/exit" {
		t.Fatal("server catalog replaced a local alias")
	}
}

func TestServerCommandOutputAndQueuedInput(t *testing.T) {
	for _, failure := range []bool{false, true} {
		t.Run(map[bool]string{false: "output", true: "failure"}[failure], func(t *testing.T) {
			release := make(chan struct{}, 1)
			f := &fakeServer{}
			srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path == "/commands" {
					_, _ = w.Write([]byte(`{"commands":[{"name":"/skills","description":"list skills"}]}`))
					return
				}
				var body map[string]any
				_ = json.NewDecoder(r.Body).Decode(&body)
				f.mu.Lock()
				f.reqs = append(f.reqs, request{r.URL.Path, body})
				f.mu.Unlock()
				if r.URL.Path == "/session/sess-1/command" {
					<-release
					if failure {
						w.WriteHeader(http.StatusServiceUnavailable)
						_, _ = w.Write([]byte(`{"detail":"discovery unavailable"}`))
					} else {
						_, _ = w.Write([]byte(`{"stdout":"review-fixture  local  Review changes","stderr":"fixture warning"}`))
					}
					return
				}
				w.WriteHeader(http.StatusAccepted)
			}))
			defer srv.Close()
			defer close(release)
			events := make(chan voss.TypedEvent)
			defer close(events)
			d := newDriver(t, voss.AttachClient(srv.URL, "test"), events)
			d.until("catalog", func() bool { return len(d.m.serverCommands) > 0 })
			d.typeText("/skills")
			d.press("enter")
			d.until("dispatch", func() bool { return len(f.requestsTo("/command")) == 1 })
			d.typeText("next prompt")
			d.press("enter")
			if d.m.commanding != "/skills" || len(d.m.queue) != 1 || len(f.requestsTo("/message")) != 0 {
				t.Fatal("command entered a model turn or failed to queue input")
			}
			release <- struct{}{}
			d.until("queued prompt", func() bool { return len(f.requestsTo("/message")) == 1 })
			if d.m.commanding != "" || len(d.m.queue) != 0 || text(f.requestsTo("/message")[0]) != "next prompt" {
				t.Fatal("command failed to release queued input")
			}
			if failure {
				if !strings.Contains(d.transcript(), "discovery unavailable") {
					t.Fatal("command error missing from transcript")
				}
			} else if !strings.Contains(d.transcript(), "review-fixture") || !strings.Contains(d.transcript(), "fixture warning") {
				t.Fatalf("command output missing: %s", d.transcript())
			}
			if f.requestsTo("/command")[0].body["name"] != "/skills" {
				t.Fatal("incorrect command dispatched")
			}
		})
	}
}

func TestMissingCommandCatalogKeepsLocalCommands(t *testing.T) {
	m := newChatModel(nil, nil, sessionMeta{}, nil)
	next, _ := m.Update(commandListMsg{err: &voss.VossError{Status: http.StatusNotFound}})
	got := next.(chatModel)
	if len(got.blocks) != 0 || !strings.Contains(got.helpText(), "/help") {
		t.Fatal("older server broke local commands or displayed a startup warning")
	}
	next, _ = got.Update(commandListMsg{err: &voss.VossError{Status: http.StatusServiceUnavailable, Detail: "catalog unavailable"}})
	if len(next.(chatModel).blocks) != 1 {
		t.Fatal("catalog failure was hidden")
	}
}

func TestStaleCommandResultCannotChangeResumedSession(t *testing.T) {
	m := newChatModel(nil, nil, sessionMeta{ID: "new"}, nil)
	m.commanding = "/agents"
	stdout := "old session tools"
	next, _ := m.Update(commandResultMsg{id: "old", result: voss.CommandResult{Stdout: &stdout}})
	got := next.(chatModel)
	if got.commanding != "/agents" || len(got.blocks) != 0 {
		t.Fatal("old response changed current command or transcript")
	}
}
