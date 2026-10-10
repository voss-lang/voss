package main

import (
	"errors"
	"fmt"
	"reflect"
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

func diffFixture() voss.DiffProposed {
	return voss.DiffProposed{Id: "d1", Hunks: []voss.DiffHunk{
		{File: "settings.go", Start: 3, Lines: []string{"- timeout := 10", "+ timeout := 30"}},
		{File: "settings.go", Start: 7, Lines: []string{"- retries := 1", "+ retries := 3"}},
	}}
}

func TestDiffReviewReplies(t *testing.T) {
	for _, tc := range []struct {
		keys      []string
		decisions []any
	}{
		{[]string{"y", "y"}, []any{"accept", "accept"}},
		{[]string{"y", "n"}, []any{"accept", "reject"}},
		{[]string{"s", "y"}, []any{"skip", "accept"}},
		{[]string{"a"}, []any{"accept", "accept"}},
		{[]string{"q"}, []any{"reject", "reject"}},
		{[]string{"y", "esc"}, []any{}},
	} {
		t.Run(strings.Join(tc.keys, "/"), func(t *testing.T) {
			f, client := newFakeServer(t)
			events := make(chan voss.TypedEvent)
			defer close(events)
			d := newDriver(t, client, events)
			d.send(windowSize(80, 24))
			d.m.turn.busy = true
			d.m.editor.SetValue("unfinished prompt")
			d.m.queue = []string{"next task"}
			d.send(eventMsg{ev: diffFixture()})
			for i, k := range tc.keys {
				d.press(k)
				if i < len(tc.keys)-1 && len(f.requestsTo("/diff")) != 0 {
					t.Fatal("partial review submitted")
				}
			}
			d.until("reply", func() bool { return d.m.review == nil })
			reqs := f.requestsTo("/diff")
			if len(reqs) != 1 || reqs[0].body["id"] != "d1" || !reflect.DeepEqual(reqs[0].body["decisions"], tc.decisions) {
				t.Fatalf("wrong reply: %+v", reqs)
			}
			if d.m.editor.Value() != "unfinished prompt" || len(d.m.queue) != 1 || len(f.requestsTo("/message")) != 0 {
				t.Fatal("review lost draft or drained queue before idle")
			}
		})
	}
}

func TestDiffReviewScrollResizeAndInputIsolation(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, client, events)
	d.send(windowSize(80, 24))
	proposal := diffFixture()
	for i := 0; i < 80; i++ {
		proposal.Hunks[0].Lines = append(proposal.Hunks[0].Lines, fmt.Sprintf("+ row %d %s", i, strings.Repeat("long detail ", 10)))
	}
	d.send(eventMsg{ev: proposal})
	d.m.editor.SetValue("draft")
	d.press("pgdown")
	if d.m.review.view.YOffset() == 0 {
		t.Fatal("page down failed")
	}
	d.press("g")
	d.send(tea.MouseWheelMsg{Button: tea.MouseWheelDown})
	if d.m.review.view.YOffset() == 0 {
		t.Fatal("mouse scroll failed")
	}
	d.send(tea.PasteMsg{Content: "must not enter draft"})
	d.typeText("xz")
	d.press("y")
	if !strings.Contains(ansi.Strip(d.m.View().Content), "[2/2] settings.go:7") {
		t.Fatal("next hunk not visible")
	}
	for _, size := range [][2]int{{120, 40}, {60, 16}, {30, 10}} {
		d.send(windowSize(size[0], size[1]))
		lines := strings.Split(d.m.View().Content, "\n")
		if len(lines) != size[1] {
			t.Fatalf("size %v: %d rows", size, len(lines))
		}
		for _, line := range lines {
			if ansi.StringWidth(line) > size[0] {
				t.Fatalf("overflow: %s", line)
			}
		}
	}
	if d.m.editor.Value() != "draft" || len(d.m.review.decisions) != 1 {
		t.Fatal("unexpected draft or decision change")
	}
}

func TestDiffReviewAbortAndResolution(t *testing.T) {
	for _, closing := range []string{"resolved", "idle", "disconnect", "abort"} {
		t.Run(closing, func(t *testing.T) {
			f, client := newFakeServer(t)
			events := make(chan voss.TypedEvent)
			defer close(events)
			d := newDriver(t, client, events)
			d.send(windowSize(80, 24))
			d.m.turn.busy = true
			d.send(eventMsg{ev: diffFixture()})
			switch closing {
			case "resolved":
				d.send(eventMsg{ev: voss.DiffResolved{Id: "other"}})
				if d.m.review == nil {
					t.Fatal("unrelated event closed review")
				}
				d.send(eventMsg{ev: voss.DiffResolved{Id: "d1"}})
			case "idle":
				d.send(eventMsg{ev: voss.SessionIdle{}})
			case "disconnect":
				d.send(streamClosedMsg{})
			case "abort":
				d.m.queue = []string{"never send"}
				d.press("ctrl+c")
				d.press("a")
				d.until("abort", func() bool { return len(f.requestsTo("/abort")) == 1 })
				if len(d.m.queue) != 0 || !d.m.turn.interrupted {
					t.Fatal("abort retained queue")
				}
				d.send(eventMsg{ev: voss.DiffResolved{Id: "d1"}})
			}
			if d.m.review != nil || len(f.requestsTo("/diff")) != 0 {
				t.Fatal("dismissal approved edits")
			}
		})
	}
}

func TestDiffReplyFailureRetryAndLateResponses(t *testing.T) {
	f, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	defer close(events)
	d := newDriver(t, client, events)
	d.send(windowSize(80, 24))
	d.send(eventMsg{ev: diffFixture()})
	d.m.review.decisions = []voss.DiffReplyDecisions{voss.Accept, voss.Accept}
	d.m.review.submitting = true
	d.send(diffReplyMsg{sessionID: "sess-1", id: "d1", err: errors.New("network failed")})
	if d.m.review == nil || d.m.review.submitting || !strings.Contains(ansi.Strip(d.m.View().Content), "Enter retry") {
		t.Fatal("failure cannot be retried")
	}
	d.press("enter")
	d.press("a")
	d.until("retry", func() bool { return d.m.review == nil })
	if len(f.requestsTo("/diff")) != 1 {
		t.Fatal("retry submitted more than once")
	}
	newer := diffFixture()
	newer.Id = "d2"
	d.send(eventMsg{ev: newer})
	d.send(diffReplyMsg{sessionID: "sess-1", id: "d1"})
	d.send(diffReplyMsg{sessionID: "old-session", id: "d2"})
	if d.m.review == nil {
		t.Fatal("late reply closed newer review")
	}
	d.send(diffReplyMsg{sessionID: "sess-1", id: "d2", stale: true})
	if d.m.review != nil || !strings.Contains(d.transcript(), "expired or was already answered") {
		t.Fatal("stale response not surfaced")
	}
}
