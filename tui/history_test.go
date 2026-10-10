package main

import (
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
	voss "github.com/vosslang/voss/sdk/go"
)

func TestPromptHistorySurvivesRestartIncludingQueuedMultilinePrompts(t *testing.T) {
	path := filepath.Join(t.TempDir(), ".config", "voss", "tui-history")
	f, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	if err := d.m.loadHistory(path); err != nil {
		t.Fatal(err)
	}
	d.typeText("first prompt")
	d.press("enter")
	d.until("send", func() bool { return len(f.requestsTo("/message")) == 1 })
	big := strings.Repeat("line\n", 7) + "quoted \"end\""
	d.send(tea.PasteMsg{Content: big})
	d.press("enter")
	if len(d.m.queue) != 1 {
		t.Fatal("second prompt should still be queued")
	}
	d.typeText("unsent draft")

	restarted := newDriver(t, client, make(chan voss.TypedEvent))
	if err := restarted.m.loadHistory(path); err != nil {
		t.Fatal(err)
	}
	if want := []string{"first prompt", big}; !reflect.DeepEqual(restarted.m.history, want) {
		t.Fatalf("history = %q, want %q", restarted.m.history, want)
	}
	restarted.press("ctrl+r")
	restarted.typeText("quoted")
	restarted.press("enter")
	if got := restarted.m.editor.Value(); got != big {
		t.Fatalf("search should restore the entire multiline prompt, got %q", got)
	}
	if runtime.GOOS != "windows" {
		for p, want := range map[string]os.FileMode{path: 0o600, filepath.Dir(path): 0o700} {
			info, err := os.Stat(p)
			if err != nil {
				t.Fatal(err)
			}
			if info.Mode().Perm() != want {
				t.Errorf("%s mode = %o, want %o", p, info.Mode().Perm(), want)
			}
		}
	}
}

func TestHistoryAppendsAcrossClientsAndSearchIncludesSessionMessages(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tui-history")
	var first, second chatModel
	for _, m := range []*chatModel{&first, &second} {
		if err := m.loadHistory(path); err != nil {
			t.Fatal(err)
		}
	}
	first.rememberPrompt("older")
	second.rememberPrompt("newer")
	first.rememberPrompt("older")
	var reloaded chatModel
	if err := reloaded.loadHistory(path); err != nil {
		t.Fatal(err)
	}
	if want := []string{"older", "newer", "older"}; !reflect.DeepEqual(reloaded.history, want) {
		t.Fatalf("one client overwrote another's history: %q", reloaded.history)
	}
	reloaded.sent = []string{"older", "session-only"}
	if want := []string{"session-only", "older", "newer"}; !reflect.DeepEqual(reloaded.searchCorpus(), want) {
		t.Fatalf("search corpus = %q, want %q", reloaded.searchCorpus(), want)
	}
}

func TestHistoryWriteFailureDoesNotLoseOrBlockThePrompt(t *testing.T) {
	f, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	d.m.historyPath = t.TempDir()
	d.typeText("still send this")
	d.press("enter")
	d.until("send", func() bool { return len(f.requestsTo("/message")) == 1 })
	if !strings.Contains(d.transcript(), "prompt history:") {
		t.Fatal("history error should be visible")
	}
	if got := d.m.searchCorpus(); len(got) != 1 || got[0] != "still send this" {
		t.Fatalf("prompt should remain searchable, got %q", got)
	}
}

func TestBrokenHistoryKeepsReadableEntriesWithoutAppendingToCorruption(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tui-history")
	data := "\"saved\"\n\"unfinished"
	if err := os.WriteFile(path, []byte(data), 0o600); err != nil {
		t.Fatal(err)
	}
	var m chatModel
	if err := m.loadHistory(path); err == nil {
		t.Fatal("expected a history read error")
	}
	m.rememberPrompt("new prompt")
	if want := []string{"new prompt", "saved"}; !reflect.DeepEqual(m.searchCorpus(), want) {
		t.Fatalf("search corpus = %q", m.searchCorpus())
	}
	got, err := os.ReadFile(path)
	if err != nil || string(got) != data {
		t.Fatalf("broken history should be left intact, got %q, %v", got, err)
	}
}
