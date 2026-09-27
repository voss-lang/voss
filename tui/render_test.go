package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

var update = flag.Bool("update", false, "rewrite the golden files in testdata/golden")

const sampleMarkdown = "## Result\n\nThe edit to `notes.txt` **worked**. A long sentence that has to wrap at sixty columns but fits on one line at one hundred and twenty.\n\n- first item\n- second item\n\n```go\nfunc main() {}\n```"

// goldenCases are rendered at 60 and 120 columns. The golden files hold the
// text with styling stripped, so they show layout and wrapping.
func goldenCases(t *testing.T) map[string]func(renderer) string {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "notes.txt"), []byte("hello\nold line here\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	long := strings.Repeat("word ", 30)
	prompt := func(tool string, args map[string]any) func(renderer) string {
		return func(r renderer) string {
			return r.permission(voss.PermissionUpdated{Id: "p", ToolName: tool, Args: &args}, dir)
		}
	}
	blk := func(kind blockKind, text string) func(renderer) string {
		return func(r renderer) string { return r.block(block{kind, text}) }
	}
	return map[string]func(renderer) string{
		"user":      blk(blockUser, "fix the bug in "+long),
		"assistant": blk(blockAssistant, sampleMarkdown),
		"plan":      blk(blockPlan, "plan: fs_read notes.txt → fs_edit notes.txt"),
		"tool":      blk(blockTool, "fs_read ✓ "+long),
		"clarify":   blk(blockClarify, "which file did you mean? "+long),
		"warning":   blk(blockWarning, "instructions is 5000 tokens, over the 4000-token budget; truncated AGENTS.md"),
		"error":     blk(blockError, "send: "+long),
		"notice":    blk(blockNotice, `unsupported event "tool.progress" from a newer server`),
		"prompt_edit_old": prompt("fs_edit", map[string]any{
			"path": "notes.txt", "old": "the quick brown fox", "new": "the slow brown fox jumps",
		}),
		"prompt_edit_anchor": prompt("fs_edit", map[string]any{
			"path": "notes.txt", "anchor": lineAnchor("old line here"), "new": "new line here",
		}),
		"prompt_edit_stale": prompt("fs_edit", map[string]any{
			"path": "notes.txt", "anchor": "deadbeef", "new": "replacement",
		}),
		"prompt_edit_many": prompt("fs_edit_many", map[string]any{
			"path":  "notes.txt",
			"edits": []any{map[string]any{"old": "a = 1", "new": "a = 2"}, map[string]any{"old": "b", "new": "c"}},
		}),
		"prompt_edit_long": prompt("fs_edit", map[string]any{
			"path": "notes.txt", "old": "", "new": strings.Repeat("line\n", 30),
		}),
		"prompt_shell": prompt("shell", map[string]any{"command": "go test ./...", "cwd": "."}),
		"prompt_scope": prompt("scope_expand", map[string]any{"target": "../other"}),
		"tool_args": func(r renderer) string {
			args := map[string]any{"path": "notes.txt", "new": "hello\nworld " + long}
			return r.block(block{blockToolArgs, toolArgsText(voss.ToolEvent{Name: "fs_edit", Args: &args})})
		},
	}
}

func TestRenderGolden(t *testing.T) {
	for name, render := range goldenCases(t) {
		for _, width := range []int{60, 120} {
			t.Run(fmt.Sprintf("%s_%d", name, width), func(t *testing.T) {
				out := render(newRenderer(width, true))
				for i, line := range strings.Split(out, "\n") {
					if w := ansi.StringWidth(line); w > width {
						t.Errorf("line %d is %d columns, wider than %d: %q", i+1, w, width, ansi.Strip(line))
					}
				}
				got := ansi.Strip(out) + "\n"
				path := filepath.Join("testdata", "golden", fmt.Sprintf("%s_%d.txt", name, width))
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
					t.Fatalf("%v (run go test -run TestRenderGolden -update)", err)
				}
				if got != string(want) {
					t.Fatalf("render changed; run with -update if intended.\n--- got\n%s--- want\n%s", got, want)
				}
			})
		}
	}
}

func TestMarkdownLinesCarryNoPadding(t *testing.T) {
	for _, line := range strings.Split(newRenderer(120, true).markdown("short"), "\n") {
		if strings.HasSuffix(ansi.Strip(line), " ") {
			t.Fatalf("trailing spaces in %q", ansi.Strip(line))
		}
	}
}

func TestDiffStylesChangedWords(t *testing.T) {
	out := newRenderer(80, true).diff("the old value", "the new value", true)
	if !strings.Contains(out, styleDel.Render("old")) || !strings.Contains(out, styleAdd.Render("new")) {
		t.Fatalf("diff did not style the changed words: %q", out)
	}
	if strings.Contains(out, styleAdd.Render("the")) || strings.Contains(out, styleDel.Render("value")) {
		t.Fatalf("diff styled unchanged words: %q", out)
	}
}
