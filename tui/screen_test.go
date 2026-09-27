package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

// screenCases drive a model into a state; the golden is the whole screen.
var screenCases = map[string]func(d *driver, events chan voss.TypedEvent){
	"home": func(d *driver, events chan voss.TypedEvent) {},
	"finished_turn": func(d *driver, events chan voss.TypedEvent) {
		for _, ev := range []voss.TypedEvent{
			voss.UserEvent{Task: "what does notes.txt say?"},
			voss.ThinkingEvent{Label: "planning 1/1"},
			voss.PlanEvent{Steps: &[]voss.PlanStep{{Name: "fs_read"}}},
			voss.ToolEvent{Name: "fs_read", State: "ok", Summary: str("2cf24dba│hello")},
			voss.FinalEvent{Text: "It says **hello**."},
			voss.StatusEvent{Model: "gpt-6-astra", Tokens: 4200, CostUsd: 0.0123, CtxPct: 0.07},
			voss.SessionIdle{},
		} {
			events <- ev
		}
		d.until("idle", func() bool { return strings.Contains(d.transcript(), "It says") && !d.m.turn.busy })
	},
	"running_turn": func(d *driver, events chan voss.TypedEvent) {
		events <- voss.UserEvent{Task: "fix the failing test"}
		events <- voss.ThinkingEvent{Label: "planning iter 1/8"}
		events <- voss.ToolEvent{Name: "shell", State: "pending"}
		d.until("pending tool", func() bool { return d.m.turn.pendingTool == "shell" })
	},
	"transcript_focused": func(d *driver, events chan voss.TypedEvent) {
		d.press("esc")
	},
}

func TestScreenGolden(t *testing.T) {
	for name, drive := range screenCases {
		for _, size := range [][2]int{{80, 24}, {120, 40}} {
			t.Run(fmt.Sprintf("%s_%dx%d", name, size[0], size[1]), func(t *testing.T) {
				_, client := newFakeServer(t)
				events := make(chan voss.TypedEvent, 16)
				meta := sessionMeta{ID: "sess-1", Cwd: "/work/project", Provider: "Anthropic", Model: "claude-sonnet-4-5", Git: "+2 ~0 -0",
					Resume: `⎇ 6f5fd6 "Reply with exactly the word pong and no…" · 14d ago`}
				d := &driver{t: t, m: newChatModel(context.Background(), client, meta, events), msgs: make(chan tea.Msg, 1024)}
				d.run(d.m.Init())
				d.send(tea.WindowSizeMsg{Width: size[0], Height: size[1]})
				drive(d, events)

				screen := d.m.View().Content
				lines := strings.Split(screen, "\n")
				if len(lines) != size[1] {
					t.Fatalf("%d lines, want %d", len(lines), size[1])
				}
				for i, line := range lines {
					if w := ansi.StringWidth(line); w > size[0] {
						t.Errorf("line %d is %d columns, wider than %d", i+1, w, size[0])
					}
					lines[i] = strings.TrimRight(ansi.Strip(line), " ")
				}
				got := strings.Join(lines, "\n") + "\n"
				got = strings.ReplaceAll(got, "⠋", "✦") // the spinner frame depends on timing
				path := filepath.Join("testdata", "screens", fmt.Sprintf("%s_%dx%d.txt", name, size[0], size[1]))
				if *update {
					if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
						t.Fatal(err)
					}
					if err := os.WriteFile(path, []byte(got), 0o644); err != nil {
						t.Fatal(err)
					}
					return
				}
				want, err := os.ReadFile(path)
				if err != nil {
					t.Fatalf("%v (run go test -run TestScreenGolden -update)", err)
				}
				if got != string(want) {
					t.Fatalf("screen changed; run with -update if intended.\n--- got\n%s--- want\n%s", got, want)
				}
			})
		}
	}
}
