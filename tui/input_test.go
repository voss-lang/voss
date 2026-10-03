package main

import (
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

func TestLargePasteBecomesAChipAndExpandsOnSubmit(t *testing.T) {
	f, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))

	big := strings.Repeat("line\n", 7) + "end"
	d.typeText("see ")
	d.send(tea.PasteMsg{Content: big})
	d.send(tea.PasteMsg{Content: big})
	if got := d.m.editor.Value(); got != "see [pasted 8 lines][pasted 8 lines #2]" {
		t.Fatalf("editor = %q", got)
	}
	d.press("backspace")
	if got := d.m.editor.Value(); got != "see [pasted 8 lines]" {
		t.Fatalf("backspace should remove the whole chip, editor = %q", got)
	}
	d.send(tea.PasteMsg{Content: "short\npaste"})
	d.press("enter")
	d.until("send", func() bool { return len(f.requestsTo("/message")) == 1 })
	if got := text(f.requestsTo("/message")[0]); got != "see "+big+"short\npaste" {
		t.Fatalf("sent %q; the chip should expand to the pasted text", got)
	}
}

func TestReverseSearchFindsEarlierMessages(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent, 8)
	d := newDriver(t, client, events)
	for _, task := range []string{"fix the parser", "run the tests", "fix the lexer", "run the tests"} {
		events <- voss.UserEvent{Task: task}
	}
	events <- voss.SessionIdle{}
	d.until("history", func() bool { return len(d.m.sent) == 4 && !d.m.turn.busy })

	d.typeText("draft")
	d.press("ctrl+r")
	d.typeText("fix")
	if got := ansi.Strip(d.m.editorView()); got != "▌ (reverse-i-search)`fix': fix the lexer" {
		t.Fatalf("search line = %q", got)
	}
	d.press("ctrl+r")
	if got := ansi.Strip(d.m.editorView()); !strings.HasSuffix(got, ": fix the parser") {
		t.Fatalf("second ctrl+r = %q, want the older match", got)
	}
	d.press("ctrl+r")
	if got := ansi.Strip(d.m.editorView()); !strings.HasSuffix(got, ": (no match)") {
		t.Fatalf("past the last match = %q", got)
	}
	d.press("esc")
	if d.m.search.active || d.m.editor.Value() != "draft" {
		t.Fatalf("esc should restore the draft, editor = %q", d.m.editor.Value())
	}

	d.press("ctrl+r")
	d.typeText("run")
	d.press("enter")
	if d.m.search.active || d.m.editor.Value() != "run the tests" {
		t.Fatalf("enter should take the match, editor = %q", d.m.editor.Value())
	}
	if n := strings.Count(strings.Join(d.m.searchCorpus(), "\n"), "run the tests"); n != 1 {
		t.Fatalf("repeated messages should appear once in the search, got %d", n)
	}
}

func TestEditingKeysKeepKilledTextAvailable(t *testing.T) {
	for _, tc := range []struct {
		name, input, want string
		keys              []string
	}{
		{"line start", "héllo world", "!héllo world", []string{"ctrl+a", "!"}},
		{"line end", "héllo world", "héllo world!", []string{"ctrl+a", "ctrl+e", "!"}},
		{"kill line", "héllo world", "héllo world", []string{"ctrl+a", "ctrl+k", "alt+y"}},
		{"kill backwards", "héllo world", "héllo world", []string{"ctrl+u", "alt+y"}},
		{"kill word backwards", "héllo world", "héllo world", []string{"ctrl+w", "alt+y"}},
		{"kill word forwards", "héllo world", "héllo world", []string{"ctrl+a", "alt+d", "alt+y"}},
		{"successive backwards kills", "one two three", "one two three", []string{"ctrl+w", "ctrl+w", "alt+y"}},
		{"successive forwards kills", "one two three", "one two three", []string{"ctrl+a", "alt+d", "alt+d", "alt+y"}},
		{"kill newline", "first\nsecond", "first\nsecond", []string{"ctrl+a", "ctrl+u", "alt+y"}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			_, client := newFakeServer(t)
			d := newDriver(t, client, make(chan voss.TypedEvent))
			d.send(windowSize(80, 24))
			d.m.editor.SetValue(tc.input)
			d.press(tc.keys...)
			if got := d.m.editor.Value(); got != tc.want {
				t.Fatalf("editor = %q, want %q", got, tc.want)
			}
		})
	}
}

func TestAltYCyclesKillsWithoutReplacingSurroundingText(t *testing.T) {
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	d.send(windowSize(30, 24))
	d.typeText("older")
	d.press("ctrl+u")
	d.typeText("newer")
	d.press("ctrl+u")
	d.m.editor.SetValue("a long first line that wraps several times\nleft right")
	d.press("ctrl+a")
	d.m.editor.SetCursorColumn(5)
	d.press("alt+y", "alt+y")
	if got := d.m.editor.Value(); got != "a long first line that wraps several times\nleft olderright" {
		t.Fatalf("cycling should replace only the last yank, got %q", got)
	}
	d.press("alt+y")
	if got := d.m.editor.Value(); !strings.HasSuffix(got, "left newerright") {
		t.Fatalf("cycling should wrap, got %q", got)
	}
	d.typeText("!")
	d.press("alt+y")
	if got := d.m.editor.Value(); !strings.HasSuffix(got, "left newer!newerright") {
		t.Fatalf("typing should start a fresh yank, got %q", got)
	}
}

func TestKilledPasteSurvivesSubmission(t *testing.T) {
	f, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	big := strings.Repeat("line\n", 7) + "end"
	d.send(tea.PasteMsg{Content: big})
	d.press("ctrl+u")
	d.typeText("another prompt")
	d.press("enter")
	d.until("send", func() bool { return len(f.requestsTo("/message")) == 1 })
	d.press("alt+y")
	if got := d.m.editor.Value(); got != big {
		t.Fatalf("kill ring should retain expanded paste, got %q", got)
	}
}
