package main

import (
	"bufio"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	voss "github.com/vosslang/voss/sdk/go"
)

// testdata/local holds results from the Python functions this ports (see
// gen.py there): sandbox.shell_allowed, shlex.split and
// voss_md.append_voss_notes_bullet.
func TestShellRulesMatchPython(t *testing.T) {
	f, err := os.Open("testdata/local/commands.golden")
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		var want struct {
			Cmd     string `json:"cmd"`
			Allowed bool   `json:"allowed"`
			Reason  string `json:"reason"`
			Split   any    `json:"split"`
		}
		if err := json.Unmarshal(sc.Bytes(), &want); err != nil {
			t.Fatal(err)
		}
		allowed, reason := shellAllowed(want.Cmd)
		if allowed != want.Allowed || reason != want.Reason {
			t.Errorf("shellAllowed(%q) = %v %q, Python says %v %q", want.Cmd, allowed, reason, want.Allowed, want.Reason)
		}
		words, err := shlexSplit(want.Cmd)
		var got any = toAny(words)
		if err != nil {
			got = "error: " + err.Error()
		}
		if !reflect.DeepEqual(got, want.Split) {
			t.Errorf("shlexSplit(%q) = %#v, Python says %#v", want.Cmd, got, want.Split)
		}
	}
}

func toAny(words []string) []any {
	out := make([]any, len(words))
	for i, w := range words {
		out[i] = w
	}
	return out
}

func TestVossNoteMatchesPython(t *testing.T) {
	sources, _ := filepath.Glob("testdata/local/vossmd/*.md")
	now := time.Date(2026, 9, 27, 12, 0, 0, 0, time.UTC)
	for _, src := range sources {
		t.Run(filepath.Base(src), func(t *testing.T) {
			path := filepath.Join(t.TempDir(), "VOSS.md")
			if body, _ := os.ReadFile(src); len(body) > 0 {
				if err := os.WriteFile(path, body, 0o644); err != nil {
					t.Fatal(err)
				}
			}
			if err := appendVossNote(path, "added note", now); err != nil {
				t.Fatal(err)
			}
			got, _ := os.ReadFile(path)
			want, _ := os.ReadFile(strings.TrimSuffix(src, ".md") + ".out")
			if string(got) != string(want) {
				t.Fatalf("differs from Python:\n--- go\n%s--- python\n%s", got, want)
			}
		})
	}
}

func TestBangAndHashLinesRunLocallyEvenMidTurn(t *testing.T) {
	f, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)
	if err := os.WriteFile(filepath.Join(d.m.cwd, "hello.txt"), []byte("hi there\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	d.typeText("start a turn")
	d.press("enter")
	d.typeText("!cat hello.txt")
	d.press("enter")
	d.until("shell block", func() bool { return strings.Contains(d.transcript(), "· exit 0") })
	if !strings.Contains(d.transcript(), "! cat hello.txt\n hi there\n · exit 0") {
		t.Fatalf("transcript:\n%s", d.transcript())
	}
	d.typeText("!rm -rf x")
	d.press("enter")
	d.until("refusal", func() bool { return strings.Contains(d.transcript(), "denied token: 'rm -rf'") })
	if !strings.Contains(d.transcript(), "· exit 1") {
		t.Fatalf("a refused command should show exit 1:\n%s", d.transcript())
	}

	d.typeText("#remember the parser")
	d.press("enter")
	note, _ := os.ReadFile(filepath.Join(d.m.cwd, "VOSS.md"))
	if !strings.Contains(string(note), "] remember the parser\n") || !strings.Contains(d.transcript(), "# note saved") {
		t.Fatalf("VOSS.md:\n%s\ntranscript:\n%s", note, d.transcript())
	}
	if len(d.m.queue) != 0 || len(f.requestsTo("/message")) != 1 {
		t.Fatalf("! and # lines should not queue or reach the server (queue %v)", d.m.queue)
	}
}
