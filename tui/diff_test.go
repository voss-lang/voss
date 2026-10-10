package main

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestWordDiff(t *testing.T) {
	for _, tc := range []struct {
		name string
		a, b string
		want []diffOp
	}{
		{"identical", "a b", "a b", []diffOp{{'=', "a b"}}},
		{"one word changed", "the old value", "the new value", []diffOp{{'=', "the "}, {'-', "old"}, {'+', "new"}, {'=', " value"}}},
		{"word inserted", "a c", "a b c", []diffOp{{'=', "a "}, {'+', "b "}, {'=', "c"}}},
		{"line appended", "hello", "hello\nworld", []diffOp{{'=', "hello"}, {'+', "\nworld"}}},
		{"from empty", "", "new", []diffOp{{'+', "new"}}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got := wordDiff(tc.a, tc.b)
			if !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("wordDiff(%q, %q) = %q, want %q", tc.a, tc.b, got, tc.want)
			}
			if before, after := rebuild(got); before != tc.a || after != tc.b {
				t.Fatalf("ops rebuild %q -> %q", before, after)
			}
		})
	}
}

func TestWordDiffOverTheCapIsOneDeleteAndOneInsert(t *testing.T) {
	a := "keep " + strings.Repeat("x ", diffTokenCap)
	b := "keep " + strings.Repeat("y ", diffTokenCap)
	ops := wordDiff(a, b)
	var dels, ins int
	for _, op := range ops {
		switch op.kind {
		case '-':
			dels++
		case '+':
			ins++
		}
	}
	if dels != 1 || ins != 1 {
		t.Fatalf("%d deletes and %d inserts, want one of each", dels, ins)
	}
	if before, after := rebuild(ops); before != a || after != b {
		t.Fatal("ops do not rebuild the inputs")
	}
}

// rebuild recovers both inputs from the ops, so any diff can be checked for loss.
func rebuild(ops []diffOp) (string, string) {
	var before, after strings.Builder
	for _, op := range ops {
		if op.kind != '+' {
			before.WriteString(op.text)
		}
		if op.kind != '-' {
			after.WriteString(op.text)
		}
	}
	return before.String(), after.String()
}

func TestLineAnchorMatchesServer(t *testing.T) {
	if got := lineAnchor("hello"); got != "2cf24dba" {
		t.Fatalf("lineAnchor(hello) = %q, want the server's 2cf24dba", got)
	}
}

func TestEditOldResolvesAnchorsFromTheFile(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "f.txt"), []byte("one\ntwo\nthree\ntwo\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		name string
		args map[string]any
		want string
		ok   bool
	}{
		{"old wins", map[string]any{"old": "x", "anchor": lineAnchor("one"), "path": "f.txt"}, "x", true},
		{"single line", map[string]any{"anchor": lineAnchor("one"), "path": "f.txt"}, "one", true},
		{"range", map[string]any{"anchor": lineAnchor("one"), "end_anchor": lineAnchor("three"), "path": "f.txt"}, "one\ntwo\nthree", true},
		{"ambiguous anchor", map[string]any{"anchor": lineAnchor("two"), "path": "f.txt"}, "", false},
		{"end before start", map[string]any{"anchor": lineAnchor("three"), "end_anchor": lineAnchor("one"), "path": "f.txt"}, "", false},
		{"stale anchor", map[string]any{"anchor": "deadbeef", "path": "f.txt"}, "", false},
		{"missing file", map[string]any{"anchor": lineAnchor("one"), "path": "nope.txt"}, "", false},
		{"absolute path", map[string]any{"anchor": lineAnchor("three"), "path": filepath.Join(dir, "f.txt")}, "three", true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, ok := editOld(dir, tc.args)
			if got != tc.want || ok != tc.ok {
				t.Fatalf("editOld = %q, %v; want %q, %v", got, ok, tc.want, tc.ok)
			}
		})
	}
}
