package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"reflect"
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

func inspectionFixture() voss.InspectionResult {
	return voss.InspectionResult{
		Title: "Probable decision",
		Text:  "Recorded decision 1\nPrevious: [0] choose parser\nNext: none\n\n[1] emit tests\nconfidence: 0.47\nprevious: 0\nnext: none\nbody:\nVerify the parser against the saved fixtures.",
	}
}

func TestInspectionPanelScrollResizeAndDraftPreservation(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, client, events)
	d.send(windowSize(80, 24))
	result := inspectionFixture()
	for i := 0; i < 80; i++ {
		result.Text += fmt.Sprintf("\nRecorded row %02d: %s", i, strings.Repeat("long detail ", 10))
	}
	d.send(commandResultMsg{id: "sess-1", result: voss.CommandResult{Inspection: &result}})
	d.m.editor.SetValue("unfinished prompt")
	if screen := ansi.Strip(d.m.View().Content); !strings.Contains(screen, "confidence: 0.47") || !strings.Contains(screen, result.Title) {
		t.Fatalf("inspection missing: %s", screen)
	}
	d.press("pgdown")
	if d.m.inspection.view.YOffset() == 0 {
		t.Fatal("page down did not scroll inspection")
	}
	d.press("G")
	if !strings.Contains(ansi.Strip(d.m.View().Content), "Recorded row 79") {
		t.Fatal("end of inspection unreachable")
	}
	d.press("g")
	d.send(tea.MouseWheelMsg{Button: tea.MouseWheelDown})
	if d.m.inspection.view.YOffset() == 0 {
		t.Fatal("mouse wheel did not scroll inspection")
	}
	d.send(tea.PasteMsg{Content: "must not enter draft"})
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
	if d.m.inspection != nil || d.m.editor.Value() != "unfinished prompt" {
		t.Fatal("closing inspection changed the draft")
	}
}

func TestInspectorCommandsPauseQueueAndKeepTranscript(t *testing.T) {
	for _, name := range []string{"/probable", "/btrace", "/vdiff"} {
		t.Run(name, func(t *testing.T) {
			release := make(chan struct{}, 1)
			f := &fakeServer{}
			srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path == "/commands" {
					_ = json.NewEncoder(w).Encode(voss.CommandCatalog{Commands: []voss.CommandInfo{{Name: name, Description: "inspect fixture"}}})
					return
				}
				var body map[string]any
				_ = json.NewDecoder(r.Body).Decode(&body)
				f.mu.Lock()
				f.reqs = append(f.reqs, request{r.URL.Path, body})
				f.mu.Unlock()
				if r.URL.Path == "/session/sess-1/command" {
					<-release
					result := inspectionFixture()
					_ = json.NewEncoder(w).Encode(voss.CommandResult{Inspection: &result, Stdout: &result.Text})
					return
				}
				w.WriteHeader(http.StatusAccepted)
			}))
			defer srv.Close()
			defer close(release)
			events := make(chan voss.TypedEvent)
			defer close(events)
			d := newDriver(t, voss.AttachClient(srv.URL, "test"), events)
			d.send(windowSize(80, 24))
			d.until("catalog", func() bool { return len(d.m.serverCommands) == 1 })
			args := []any{"saved run"}
			if name == "/probable" {
				args = append(args, "--decision", "1")
			}
			command := name + ` "saved run"`
			if name == "/probable" {
				command += " --decision 1"
			}
			d.typeText(command)
			d.press("enter")
			d.until("command", func() bool { return len(f.requestsTo("/command")) == 1 })
			body := f.requestsTo("/command")[0].body
			if body["name"] != name || !reflect.DeepEqual(body["args"], args) {
				t.Fatalf("incorrect command: %v", body)
			}
			d.typeText("follow up")
			d.press("enter")
			release <- struct{}{}
			d.until("inspection", func() bool { return d.m.inspection != nil })
			if len(d.m.queue) != 1 || len(f.requestsTo("/message")) != 0 {
				t.Fatal("queued work started while inspection was open")
			}
			if !strings.Contains(d.transcript(), "confidence: 0.47") {
				t.Fatal("inspection missing from transcript")
			}
			d.press("enter")
			d.until("follow up", func() bool { return len(f.requestsTo("/message")) == 1 })
			if d.m.inspection != nil || text(f.requestsTo("/message")[0]) != "follow up" {
				t.Fatal("closing inspection did not resume queued work")
			}
		})
	}
}

func TestInspectionInterruptClearsQueueAndStaleResultIsIgnored(t *testing.T) {
	m := newChatModel(nil, nil, sessionMeta{ID: "current"}, nil)
	result := inspectionFixture()
	next, _ := m.Update(commandResultMsg{id: "old", result: voss.CommandResult{Inspection: &result}})
	if next.(chatModel).inspection != nil {
		t.Fatal("stale response opened an inspection")
	}
	m.showInspection(result)
	m.queue = []string{"queued prompt"}
	next, cmd := m.Update(key("ctrl+c"))
	got := next.(chatModel)
	if got.inspection != nil || len(got.queue) != 0 || cmd != nil || got.quitting {
		t.Fatal("interrupt failed to close inspection and clear queue")
	}
}
