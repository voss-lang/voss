package main

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

func TestRankCommandsLikeTextual(t *testing.T) {
	names := commandNames()
	if got := rankCommands("/d", names, nil); !reflect.DeepEqual(got, []string{"/diff", "/doctor", "/mode"}) {
		t.Fatalf("/d = %v", got)
	}
	if got := rankCommands("/o", names, nil); !reflect.DeepEqual(got, []string{"/cost", "/doctor", "/mode", "/memory"}) {
		t.Fatalf("/o = %v; position of the match, then name", got)
	}
	if got := rankCommands("", names, []string{"/mode", "/gone"}); got[0] != "/mode" || got[1] != "/cost" {
		t.Fatalf("empty query = %v; recent first, then alphabetical", got)
	}
	if got := rankCommands("/mode edit", names, nil); len(got) != 0 {
		t.Fatalf("arguments should match nothing, got %v", got)
	}
}

func TestRankFilesLikeTextual(t *testing.T) {
	paths := []string{"cmd/main.go", "main.go", "docs/domain.md", "src/app/main_test.go", "README.md"}
	if got := rankFiles("main", paths); !reflect.DeepEqual(got, []string{"main.go", "cmd/main.go", "src/app/main_test.go", "docs/domain.md"}) {
		t.Fatalf("main = %v", got)
	}
	if got := rankFiles("", paths); !reflect.DeepEqual(got, []string{"main.go", "README.md", "cmd/main.go", "docs/domain.md", "src/app/main_test.go"}) {
		t.Fatalf("empty query = %v; shallow first, then case-insensitive name", got)
	}
}

func TestFindMentionToken(t *testing.T) {
	for _, tc := range []struct {
		text   string
		cursor int
		query  string
		ok     bool
	}{
		{"look at @src/ma", 15, "src/ma", true},
		{"look at @src/ma now", 19, "", false},
		{"email@host", 10, "host", true},
		{"@", 1, "", true},
		{"plain", 5, "", false},
	} {
		_, q, ok := findMentionToken([]rune(tc.text), tc.cursor)
		if q != tc.query || ok != tc.ok {
			t.Errorf("findMentionToken(%q, %d) = %q %v", tc.text, tc.cursor, q, ok)
		}
	}
}

func TestGatherFilesSkipsDotAndBuildDirs(t *testing.T) {
	dir := t.TempDir()
	for _, f := range []string{"a.go", "pkg/b.go", ".git/config", "node_modules/x/y.js", ".hidden/z", "build/out.bin"} {
		p := filepath.Join(dir, f)
		os.MkdirAll(filepath.Dir(p), 0o755)
		os.WriteFile(p, nil, 0o644)
	}
	got := gatherFiles(dir)
	if !reflect.DeepEqual(got, []string{"a.go", "pkg/b.go"}) {
		t.Fatalf("gatherFiles = %v", got)
	}
}

func TestSlashPaletteRunsTheHighlightedCommand(t *testing.T) {
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	d.send(windowSize(80, 24))

	d.typeText("/d")
	if d.m.pal.kind != paletteSlash || !reflect.DeepEqual(d.m.pal.names, []string{"/diff", "/doctor", "/mode"}) {
		t.Fatalf("palette = %+v", d.m.pal)
	}
	box := ansi.Strip(d.m.bottom())
	if !strings.Contains(box, "│/diff            show working-tree diff") || strings.Contains(box, "▌ voss") {
		t.Fatalf("the palette should replace the status line:\n%s", box)
	}
	d.press("down")
	if d.m.pal.idx != 1 {
		t.Fatalf("down should move to /doctor, idx %d", d.m.pal.idx)
	}
	d.press("esc")
	if d.m.pal.kind != paletteNone || d.m.editor.Value() != "/d" {
		t.Fatal("esc should close the palette and keep the text")
	}
	d.press("backspace")
	d.typeText("he")
	d.press("enter")
	if !strings.Contains(d.transcript(), "\n  \n  Control\n    /help  show this list") || d.m.editor.Value() != "" {
		t.Fatalf("/help via the palette:\n%s", d.transcript())
	}
	if d.m.recentCommands[0] != "/help" {
		t.Fatalf("recent = %v", d.m.recentCommands)
	}
}

func TestMentionPaletteInsertsThePath(t *testing.T) {
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	for _, f := range []string{"cmd/main.go", "main.go"} {
		p := filepath.Join(d.m.cwd, f)
		os.MkdirAll(filepath.Dir(p), 0o755)
		os.WriteFile(p, nil, 0o644)
	}
	d.typeText("look at @mai")
	if d.m.pal.kind != paletteMention || d.m.pal.names[0] != "main.go" {
		t.Fatalf("palette = %+v", d.m.pal)
	}
	d.press("down", "enter")
	if got := d.m.editor.Value(); got != "look at cmd/main.go " {
		t.Fatalf("editor = %q", got)
	}
	if d.m.pal.kind != paletteNone {
		t.Fatal("choosing a file should close the palette")
	}
}

func windowSize(w, h int) tea.WindowSizeMsg { return tea.WindowSizeMsg{Width: w, Height: h} }
