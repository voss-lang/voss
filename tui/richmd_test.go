package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/charmbracelet/x/ansi"
)

// The goldens in testdata/richmd are Rich's own renders (see gen.py there),
// so these tests pin the Go port to the renderer the Textual TUI uses.
func TestRichMarkdownMatchesRich(t *testing.T) {
	sources, _ := filepath.Glob("testdata/richmd/*.md")
	if len(sources) == 0 {
		t.Fatal("no markdown samples")
	}
	for _, src := range sources {
		name := strings.TrimSuffix(filepath.Base(src), ".md")
		body, err := os.ReadFile(src)
		if err != nil {
			t.Fatal(err)
		}
		for _, width := range []string{"40", "74"} {
			t.Run(name+"_"+width, func(t *testing.T) {
				want, err := os.ReadFile(filepath.Join("testdata", "richmd", name+"_"+width+".txt"))
				if err != nil {
					t.Fatal(err)
				}
				w := 40
				if width == "74" {
					w = 74
				}
				lines := strings.Split(ansi.Strip(richMarkdown(string(body), w)), "\n")
				for i := range lines {
					lines[i] = strings.TrimRight(lines[i], " ")
				}
				for len(lines) > 0 && lines[len(lines)-1] == "" {
					lines = lines[:len(lines)-1]
				}
				got := strings.Join(lines, "\n") + "\n"
				if got != string(want) {
					t.Fatalf("differs from Rich:\n--- go\n%s--- rich\n%s", got, want)
				}
			})
		}
	}
}
