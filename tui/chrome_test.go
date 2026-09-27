package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/charmbracelet/x/ansi"
)

func TestStatusLineMatchesTextual(t *testing.T) {
	got := ansi.Strip(statusLine(110, "Anthropic", "claude-sonnet-4-5", "plan", 0, 0, "+2 ~0 -0"))
	left, right := " ▌ voss · Anthropic / claude-sonnet-4-5 · plan ", " ▱▱▱▱ 0% · $0.00 · +2 ~0 -0 "
	if ansi.StringWidth(got) != 110 || !strings.HasPrefix(got, left) || !strings.HasSuffix(got, right) ||
		strings.TrimSpace(got[len(left):len(got)-len(right)]) != "" {
		t.Fatalf("status line = %q", got)
	}
}

func TestStatusLineCutsTheLeftZoneFirst(t *testing.T) {
	got := ansi.Strip(statusLine(40, "Anthropic", "claude-sonnet-4-5", "plan", 0.5, 0.25, "clean"))
	if ansi.StringWidth(got) != 40 || !strings.HasSuffix(got, "▰▰▱▱ 50% · $0.25 · clean ") || !strings.Contains(got, "…") {
		t.Fatalf("narrow status line = %q", got)
	}
}

func TestContextBarRoundsAndColoursLikeTextual(t *testing.T) {
	for _, tc := range []struct {
		pct    float64
		bar    string
		colour string
	}{
		{0.125, "▱▱▱▱", palette.Dim}, // 0.5 cells rounds half to even: 0
		{0.375, "▰▰▱▱", palette.Dim}, // 1.5 cells rounds to 2
		{0.74, "▰▰▰▱", palette.Dim},
		{0.75, "▰▰▰▱", palette.Warn},
		{1.2, "▰▰▰▰", palette.Error},
	} {
		line := statusLine(80, "", "m", "", tc.pct, 0, "")
		if !strings.Contains(ansi.Strip(line), tc.bar) {
			t.Errorf("pct %v: bar missing %q in %q", tc.pct, tc.bar, ansi.Strip(line))
		}
		if !strings.Contains(line, colourSGR(tc.colour)) {
			t.Errorf("pct %v: bar not coloured %s", tc.pct, tc.colour)
		}
	}
}

func TestCostOverADollarIsRed(t *testing.T) {
	if line := statusLine(80, "", "m", "", 0, 1.5, ""); !strings.Contains(line, colourSGR(palette.Error)+"$1.50") {
		t.Fatalf("cost not red: %q", line)
	}
}

// colourSGR is the truecolor foreground sequence lipgloss emits for a hex colour.
func colourSGR(h string) string {
	var r, g, b int
	fmt.Sscanf(h, "#%02x%02x%02x", &r, &g, &b)
	return fmt.Sprintf("38;2;%d;%d;%dm", r, g, b)
}

func TestPromptTintMatchesTextualBlend(t *testing.T) {
	r, g, b, _ := blend(palette.Accent, palette.Surface, 0.15).RGBA()
	if got := fmt.Sprintf("#%02x%02x%02x", r>>8, g>>8, b>>8); got != "#3e251c" {
		t.Fatalf("accent 15%% over surface = %s, Textual draws #3e251c", got)
	}
}

func TestProviderLabel(t *testing.T) {
	for auth, want := range map[string]string{
		"codex-oauth": "Codex", "claude-agent": "Anthropic", "env-openai": "OpenAI", "ollama": "ollama",
	} {
		if got := providerLabel(auth); got != want {
			t.Errorf("providerLabel(%q) = %q, want %q", auth, got, want)
		}
	}
}

func TestGitSummaryCountsFilesLikeTheCLI(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("no git")
	}
	dir := t.TempDir()
	if got := gitSummary(dir); got != "not a git repo" {
		t.Fatalf("outside a repo: %q", got)
	}
	git := func(args ...string) {
		cmd := exec.Command("git", append([]string{"-c", "user.email=t@t", "-c", "user.name=t"}, args...)...)
		cmd.Dir = dir
		if out, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("git %v: %v\n%s", args, err, out)
		}
	}
	write := func(name, body string) {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	git("init", "-q")
	write("a.txt", "a")
	write("b.txt", "b")
	git("add", ".")
	git("commit", "-qm", "init")
	if got := gitSummary(dir); got != "clean" {
		t.Fatalf("clean repo: %q", got)
	}
	write("a.txt", "changed")
	write("new.txt", "n")
	git("rm", "-q", "b.txt")
	if got := gitSummary(dir); got != "+1 ~1 -1" {
		t.Fatalf("summary = %q, want +1 ~1 -1", got)
	}
}

func TestWorkingLineMatchesTextual(t *testing.T) {
	for _, tc := range []struct {
		frame  int
		tokens int
		want   string
	}{
		{-1, 0, "✦ working · 12s · ctrl+c to interrupt"},
		{2, 1234, "⠹ working · 12s · 1.2k tok · ctrl+c to interrupt"},
		{0, 42, "⠋ working · 12s · 42 tok · ctrl+c to interrupt"},
	} {
		if got := ansi.Strip(workingLine(tc.frame, "working", 12500*time.Millisecond, tc.tokens)); got != tc.want {
			t.Errorf("got %q, want %q", got, tc.want)
		}
	}
}

func TestInputBoxFillsTheWidth(t *testing.T) {
	for _, width := range []int{40, 110} {
		lines := strings.Split(inputBox(width, "line one\nline two", true), "\n")
		if len(lines) != 4 {
			t.Fatalf("width %d: %d lines, want 2 text lines inside a border", width, len(lines))
		}
		for i, line := range lines {
			if w := ansi.StringWidth(line); w != width {
				t.Errorf("width %d: line %d is %d columns: %q", width, i, w, ansi.Strip(line))
			}
		}
		if got := ansi.Strip(lines[1]); !strings.HasPrefix(got, " │▌  line one") {
			t.Errorf("first text line = %q", got)
		}
	}
}

func TestToastSitsTopRightWithoutWideningTheScreen(t *testing.T) {
	screen := strings.Repeat("x", 80) + "\nsecond"
	got := strings.Split(overlayToast(screen, "⏵ planning 1/1", 80), "\n")
	if ansi.StringWidth(got[0]) != 80 || !strings.HasSuffix(ansi.Strip(got[0]), " ⏵ planning 1/1 ") || got[1] != "second" {
		t.Fatalf("toast row = %q", ansi.Strip(got[0]))
	}
	long := ansi.Strip(overlayToast(strings.Repeat("x", 80), strings.Repeat("y", 90), 80))
	if n := strings.Count(long, "y"); n != 58 {
		t.Fatalf("toast shows %d characters, Textual caps it at 60 with padding", n)
	}
}
