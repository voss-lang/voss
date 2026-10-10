package main

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/charmbracelet/x/ansi"
)

func TestRelativeAge(t *testing.T) {
	now := time.Date(2026, 9, 27, 12, 0, 0, 0, time.UTC)
	for iso, want := range map[string]string{
		"2026-09-27T11:59:30+00:00": "just now",
		"2026-09-27T11:15:00+00:00": "45m ago",
		"2026-09-27T09:00:00":       "3h ago", // no zone: read as UTC, like Python
		"2026-09-13T12:00:00+00:00": "14d ago",
		"2026-09-27T13:00:00+00:00": "just now",
		"not a date":                "",
	} {
		if got := relativeAge(iso, now); got != want {
			t.Errorf("relativeAge(%q) = %q, want %q", iso, got, want)
		}
	}
}

func TestResumeRowSkipsTheCurrentSessionAndCutsTheTask(t *testing.T) {
	dir := t.TempDir()
	sessions := filepath.Join(dir, ".voss", "sessions")
	if err := os.MkdirAll(sessions, 0o755); err != nil {
		t.Fatal(err)
	}
	for name, body := range map[string]string{
		"current.json": `{"id":"current9999","updated_at":"2026-09-27T11:59:00+00:00","turns":[{"role":"user","content":"now"}]}`,
		"older.json":   `{"id":"6f5fd6abcdef","updated_at":"2026-09-13T12:00:00+00:00","turns":[{"role":"assistant","content":"x"},{"role":"user","content":"Reply with exactly the word pong and nothing else please"}]}`,
		"oldest.json":  `{"id":"aaaaaa","updated_at":"2026-09-01T00:00:00+00:00","turns":[]}`,
	} {
		if err := os.WriteFile(filepath.Join(sessions, name), []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	now := time.Date(2026, 9, 27, 12, 0, 0, 0, time.UTC)
	want := `⎇ 6f5fd6 "Reply with exactly the word pong and no…" · 14d ago`
	if got := resumeRow(dir, "current9999", now); got != want {
		t.Fatalf("resumeRow = %q\nwant       %q", got, want)
	}
	if got := resumeRow(t.TempDir(), "x", now); got != "" {
		t.Fatalf("no sessions should give no row, got %q", got)
	}
}

// Measured from the Textual TUI at 80 columns: a word too long for the line
// starts a new line and is chopped at the width.
func TestRichWrapFoldsLongWordsOnANewLine(t *testing.T) {
	got := richWrap("cwd      /private/tmp/claude-502/-Users-benjaminmarks-Projects-Voss/552b42e8-0f1d-4088-b0a6-77fcfa4eb5b0/scratchpad/proj-m2  (not a git repo)", 76)
	want := []string{
		"cwd",
		"/private/tmp/claude-502/-Users-benjaminmarks-Projects-Voss/552b42e8-0f1d-408",
		"8-b0a6-77fcfa4eb5b0/scratchpad/proj-m2  (not a git repo)",
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("richWrap =\n%q\nwant\n%q", got, want)
	}
}

func TestHomeScreenLayout(t *testing.T) {
	rows := [][2]string{{"cwd", "~/Projects/Voss-ADE  (+2 ~0 -0)"}, {"model", "Anthropic / claude-sonnet-4-5"}}
	wide := strings.Split(ansi.Strip(homeScreen(120, 40, rows)), "\n")
	if wide[4] != strings.Repeat(" ", 46)+vossLogo[0] {
		t.Fatalf("logo line = %q", wide[4])
	}
	if !strings.Contains(strings.Join(wide, "\n"), "cwd      ~/Projects/Voss-ADE  (+2 ~0 -0)\n") ||
		!strings.HasSuffix(wide[len(wide)-1], emptyHeading) {
		t.Fatalf("home screen:\n%s", strings.Join(wide, "\n"))
	}
	narrow := ansi.Strip(homeScreen(60, 24, nil))
	if strings.Contains(narrow, "____") || !strings.Contains(narrow, "VOSS") {
		t.Fatalf("under 70 columns the logo should be the word VOSS:\n%s", narrow)
	}
}
