package main

import (
	"strings"
	"testing"
	"time"

	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

// Expected metrics follow tool_card._metric.
func TestToolCardMetric(t *testing.T) {
	sec := func(ms int) time.Duration { return time.Duration(ms) * time.Millisecond }
	for _, tc := range []struct {
		card toolCard
		want string
	}{
		{toolCard{name: "shell_run", summary: "[exit 0]", elapsed: sec(1234)}, "exit 0 · 1.2s"},
		{toolCard{name: "shell_run", summary: "<denied: nope>", elapsed: sec(12600)}, "13s"},
		{toolCard{name: "fs_edit", args: map[string]any{"old": "a\nb", "new": "c"}}, "+1 -2"},
		{toolCard{name: "fs_edit", args: map[string]any{"anchor": "2cf24dba", "new": "x"}, summary: "edited notes.txt (+3 lines)"}, "+3 lines"},
		{toolCard{name: "fs_write", args: map[string]any{"content": "one\ntwo\n"}}, "+2 -0"},
		{toolCard{name: "fs_edit_many", args: map[string]any{"edits": []any{
			map[string]any{"old": "a", "new": "b\nc"}, map[string]any{"old": "d\ne", "new": ""}}}}, "+3 -3"},
		{toolCard{name: "fs_read", summary: "2cf24dba│hello", elapsed: sec(50)}, "0.1s"},
		{toolCard{name: "fs_grep", summary: "a.go:1: x", elapsed: sec(300)}, "0.3s"},
	} {
		if got := tc.card.metric(); got != tc.want {
			t.Errorf("%s %v: metric = %q, want %q", tc.card.name, tc.card.args, got, tc.want)
		}
	}
}

func TestPyReprMatchesPython(t *testing.T) {
	for v, want := range map[any]string{
		"plain":    "'plain'",
		"it's":     `"it's"`,
		"a\nb":     `'a\nb'`,
		true:       "True",
		nil:        "None",
		float64(3): "3",
		1.5:        "1.5",
	} {
		if got := pyRepr(v); got != want {
			t.Errorf("pyRepr(%#v) = %q, want %q", v, got, want)
		}
	}
	if got := pyStr([]any{"x", float64(2), map[string]any{"k": false}}); got != "['x', 2, {'k': False}]" {
		t.Fatalf("pyStr(list) = %q", got)
	}
}

func TestToolCardsOpenSettleAndPairByNameAndArgs(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent, 16)
	d := newDriver(t, client, events)
	d.send(windowSize(100, 30))
	readA := map[string]any{"path": "a.txt"}
	readB := map[string]any{"path": "b.txt"}
	events <- voss.UserEvent{Task: "read both"}
	events <- voss.ToolEvent{Name: "fs_read", State: "pending", Args: &readA}
	events <- voss.ToolEvent{Name: "fs_read", State: "pending", Args: &readB}
	d.until("two running cards", func() bool { return len(d.m.blocks) == 3 })
	if c := d.m.blocks[1].card; c == nil || c.state != "running" || d.m.turn.pendingTool != "fs_read" {
		t.Fatalf("first card = %+v", c)
	}
	if head := ansi.Strip(d.m.rendered[1]); !strings.HasPrefix(head, "⠋ fs_read path=a.txt") {
		t.Fatalf("running head = %q", head)
	}

	// b settles first: parallel reads finish in any order.
	events <- voss.ToolEvent{Name: "fs_read", State: "ok", Args: &readB, Summary: str("b contents")}
	events <- voss.ToolEvent{Name: "fs_read", State: "ok", Args: &readA, Summary: str("a contents")}
	d.until("settled", func() bool { return d.m.blocks[1].card.state == "ok" && d.m.blocks[2].card.state == "ok" })
	if d.m.blocks[1].card.summary != "a contents" || d.m.blocks[2].card.summary != "b contents" {
		t.Fatal("results landed on the wrong cards")
	}
	if len(d.m.blocks) != 3 {
		t.Fatalf("%d blocks, want one card per call", len(d.m.blocks))
	}

	denied := map[string]any{"cmd": "rm -rf /"}
	events <- voss.ToolEvent{Name: "shell_run", State: "error", Args: &denied, Summary: str("<denied: denied token: 'rm -rf'>")}
	d.until("settled-first card", func() bool { return len(d.m.blocks) == 4 })
	c := d.m.blocks[3].card
	if c.state != "error" || !c.expanded {
		t.Fatalf("a denied call should arrive as an expanded error card, got %+v", c)
	}
	if !strings.Contains(ansi.Strip(d.m.rendered[3]), "   <denied: denied token: 'rm -rf'>") {
		t.Fatalf("error card:\n%s", ansi.Strip(d.m.rendered[3]))
	}
}

func TestCtrlOAndNavEnterToggleCards(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent, 8)
	d := newDriver(t, client, events)
	d.send(windowSize(100, 30))
	edit := map[string]any{"path": "n.txt", "old": "old line", "new": "new line"}
	events <- voss.ToolEvent{Name: "fs_edit", State: "ok", Args: &edit, Summary: str("edited n.txt (+0 lines)")}
	d.until("card", func() bool { return len(d.m.blocks) == 1 })
	if got := ansi.Strip(d.m.rendered[0]); !strings.Contains(got, "+1 -1") || !strings.Contains(got, "⎿ ▸ 1 hunk · ctrl+d full diff") {
		t.Fatalf("collapsed edit card:\n%s", got)
	}
	d.press("ctrl+o")
	if got := ansi.Strip(d.m.rendered[0]); !strings.Contains(got, "   - old line\n   + new line") {
		t.Fatalf("ctrl+o should expand every card:\n%s", got)
	}
	events <- voss.ToolEvent{Name: "fs_edit", State: "ok", Args: &edit, Summary: str("edited n.txt (+0 lines)")}
	d.until("second card", func() bool { return len(d.m.blocks) == 2 })
	if !d.m.blocks[1].card.expanded {
		t.Fatal("cards added while expand-all is on should open expanded")
	}
	d.press("ctrl+o", "esc", "enter")
	if !d.m.blocks[1].card.expanded || d.m.blocks[0].card.expanded {
		t.Fatal("enter in nav mode should toggle only the focused card")
	}
}
