package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

func codeFixture() voss.CodeResults {
	results := voss.CodeResults{Query: "/refs sample_entry", Truncated: true}
	for i := 1; i <= 50; i++ {
		results.Items = append(results.Items, voss.CodeHit{
			File: fmt.Sprintf("src/module_%02d.py", i), Line: i, Name: "sample_entry",
			Source: "regex", Language: "python", Snippet: "    result = sample_entry(argument)",
		})
	}
	return results
}

func TestCodePanelScrollResizeAndInputIsolation(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, client, events)
	d.send(windowSize(80, 24))
	results := codeFixture()
	d.send(commandResultMsg{id: "sess-1", result: voss.CommandResult{Code: &results}})
	d.m.editor.SetValue("unfinished prompt")
	if screen := ansi.Strip(d.m.View().Content); !strings.Contains(screen, "src/module_01.py:1") || !strings.Contains(screen, "sample_entry(argument)") {
		t.Fatalf("code results missing: %s", screen)
	}
	d.press("pgdown")
	if d.m.code.view.YOffset() == 0 {
		t.Fatal("page down did not scroll results")
	}
	d.press("G")
	if !strings.Contains(ansi.Strip(d.m.View().Content), "src/module_50.py:50") {
		t.Fatal("end of results unreachable")
	}
	d.press("g")
	d.send(tea.MouseWheelMsg{Button: tea.MouseWheelDown})
	if d.m.code.view.YOffset() == 0 {
		t.Fatal("mouse wheel did not scroll results")
	}
	d.send(tea.PasteMsg{Content: "must not enter the prompt"})
	d.typeText("xyz")
	for _, size := range [][2]int{{120, 40}, {60, 16}, {30, 10}} {
		d.send(windowSize(size[0], size[1]))
		lines := strings.Split(d.m.View().Content, "\n")
		if len(lines) != size[1] {
			t.Fatalf("size %v has %d rows", size, len(lines))
		}
		for _, line := range lines {
			if ansi.StringWidth(line) > size[0] {
				t.Fatalf("line overflows %d columns: %s", size[0], line)
			}
		}
	}
	d.press("esc")
	if d.m.code != nil || d.m.editor.Value() != "unfinished prompt" {
		t.Fatal("closing results discarded or changed the draft")
	}
}

func TestCodeCommandPanelPausesQueueUntilDismissed(t *testing.T) {
	release := make(chan struct{}, 1)
	f := &fakeServer{}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/commands" {
			_, _ = w.Write([]byte(`{"commands":[{"name":"/refs","description":"find references"},{"name":"/refresh","description":"rebuild index"}]}`))
			return
		}
		var body map[string]any
		_ = json.NewDecoder(r.Body).Decode(&body)
		f.mu.Lock()
		f.reqs = append(f.reqs, request{r.URL.Path, body})
		f.mu.Unlock()
		if body["name"] == "/refs" {
			<-release
			results := codeFixture()
			_ = json.NewEncoder(w).Encode(voss.CommandResult{Code: &results, Stdout: str("reference results")})
		} else if body["name"] == "/refresh" {
			_, _ = w.Write([]byte(`{"stdout":"refreshed code index: 1 files, 1 symbols"}`))
		} else {
			w.WriteHeader(http.StatusAccepted)
		}
	}))
	defer srv.Close()
	defer close(release)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, voss.AttachClient(srv.URL, "test"), events)
	d.send(windowSize(80, 24))
	d.until("catalog", func() bool { return len(d.m.serverCommands) == 2 })
	d.typeText("/refs sample_entry")
	d.press("enter")
	d.until("reference request", func() bool { return len(f.requestsTo("/command")) == 1 })
	if !strings.Contains(ansi.Strip(d.m.bottom()), "searching code") {
		t.Fatal("code lookup has no progress status")
	}
	d.typeText("/refresh")
	d.press("enter")
	d.typeText("follow up")
	d.press("enter")
	if len(d.m.queue) != 2 || len(f.requestsTo("/command")) != 1 {
		t.Fatal("palette selection bypassed the running command")
	}
	release <- struct{}{}
	d.until("results panel", func() bool { return d.m.code != nil })
	if len(d.m.queue) != 2 || len(f.requestsTo("/message")) != 0 {
		t.Fatal("queued work started before results were dismissed")
	}
	d.press("enter")
	d.until("follow up", func() bool { return len(f.requestsTo("/message")) == 1 })
	if len(f.requestsTo("/command")) != 2 || text(f.requestsTo("/message")[0]) != "follow up" || !strings.Contains(d.transcript(), "refreshed code index") {
		t.Fatal("closing results did not resume queued work in order")
	}
}

func TestCodePanelInterruptClearsQueuedInput(t *testing.T) {
	m := newChatModel(nil, nil, sessionMeta{}, nil)
	m.showCodeResults(codeFixture())
	m.queue = []string{"queued prompt"}
	next, cmd := m.Update(key("ctrl+c"))
	got := next.(chatModel)
	if got.code != nil || len(got.queue) != 0 || cmd != nil || got.quitting {
		t.Fatal("interrupt submitted queued input or quit instead of closing results")
	}
}
