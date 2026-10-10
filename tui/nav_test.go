package main

import (
	"fmt"
	"strings"
	"testing"

	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

func TestNavModeMovesFocusAndCopiesBlocks(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent, 8)
	d := newDriver(t, client, events)
	d.send(windowSize(80, 24))
	events <- voss.UserEvent{Task: "first question"}
	events <- voss.FinalEvent{Text: "first answer"}
	events <- voss.SessionIdle{}
	d.until("turn", func() bool { return len(d.m.blocks) == 2 && !d.m.turn.busy })

	d.press("esc")
	if !d.m.navMode || d.m.navIdx != 1 {
		t.Fatalf("esc should focus the last block, idx %d", d.m.navIdx)
	}
	tinted := blend(palette.Accent, palette.Bg, 0.08)
	r, g, b, _ := tinted.RGBA()
	if seq := fmt.Sprintf("48;2;%d;%d;%dm", r>>8, g>>8, b>>8); !strings.Contains(d.m.vp.View(), seq) || seq != "48;2;36;23;19m" {
		t.Fatalf("focused block should carry Textual's nav tint %s", seq)
	}
	d.press("k", "k", "k")
	if d.m.navIdx != 0 {
		t.Fatalf("k should stop at the first block, idx %d", d.m.navIdx)
	}
	d.press("y")
	d.until("copy", func() bool { return d.clipboard == "first question" })
	if d.m.toast != "copied block" {
		t.Fatalf("toast = %q", d.m.toast)
	}
	d.press("G")
	if d.m.navIdx != 1 || !d.m.follow {
		t.Fatal("G should focus the last block and follow again")
	}
	d.press("g", "g")
	if d.m.navIdx != 0 {
		t.Fatal("g g should focus the first block")
	}
	d.press("i")
	if d.m.navMode || d.m.navIdx != -1 {
		t.Fatal("i should return to the input")
	}
	d.until("toast expires", func() bool { return d.m.toast == "" })
}

func TestCtrlYCopiesTheLastCodeBlockOrAnswer(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent, 8)
	d := newDriver(t, client, events)

	d.press("ctrl+y")
	if d.m.toast != "nothing to copy yet" {
		t.Fatalf("toast = %q", d.m.toast)
	}
	events <- voss.FinalEvent{Text: "Run this:\n\n```sh\ngo test ./...\n```\n\nand then\n\n```\nsecond\nblock\n```"}
	d.until("answer", func() bool { return d.m.lastResponse != "" })
	d.press("ctrl+y")
	d.until("copy", func() bool { return d.clipboard == "second\nblock" })
	if d.m.toast != "copied code block" {
		t.Fatalf("toast = %q", d.m.toast)
	}
	events <- voss.FinalEvent{Text: "  plain answer  "}
	d.until("second answer", func() bool { return d.m.lastResponse == "  plain answer  " })
	d.press("ctrl+y")
	d.until("copy", func() bool { return d.clipboard == "plain answer" })
	if d.m.toast != "copied response" {
		t.Fatalf("toast = %q", d.m.toast)
	}
}

func TestTrimKeepsTheNewest400BlocksBehindAPlaceholder(t *testing.T) {
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	d.send(windowSize(80, 24))
	for i := range 520 {
		d.m.add(roleBlock("system", fmt.Sprintf("line %d", i)))
	}
	if len(d.m.blocks) != 419 || d.m.trimmed != 101 {
		t.Fatalf("%d blocks, %d trimmed; want 419: one trim at 501 blocks down to 400, then 19 more", len(d.m.blocks), d.m.trimmed)
	}
	d.m.layout()
	d.m.vp.GotoTop()
	if top := strings.TrimRight(ansi.Strip(strings.Split(d.m.vp.View(), "\n")[0]), " "); top != "≈ 101 earlier turns · /resume to reload" {
		t.Fatalf("first line = %q", top)
	}
}
