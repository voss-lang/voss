package main

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"strings"
	"unicode"
)

type diffOp struct {
	kind byte // '=', '-' or '+'
	text string
}

// diffTokenCap bounds the quadratic LCS table; a larger changed middle shows as delete + insert.
const diffTokenCap = 600

// wordDiff diffs a and b by runs of whitespace and non-whitespace.
func wordDiff(a, b string) []diffOp {
	x, y := tokenize(a), tokenize(b)
	pre := 0
	for pre < len(x) && pre < len(y) && x[pre] == y[pre] {
		pre++
	}
	suf := 0
	for suf < len(x)-pre && suf < len(y)-pre && x[len(x)-1-suf] == y[len(y)-1-suf] {
		suf++
	}
	var ops []diffOp
	add := func(kind byte, toks []string) {
		if len(toks) == 0 {
			return
		}
		text := strings.Join(toks, "")
		if n := len(ops); n > 0 && ops[n-1].kind == kind {
			ops[n-1].text += text
			return
		}
		ops = append(ops, diffOp{kind, text})
	}
	add('=', x[:pre])
	mx, my := x[pre:len(x)-suf], y[pre:len(y)-suf]
	if len(mx) > diffTokenCap || len(my) > diffTokenCap {
		add('-', mx)
		add('+', my)
	} else {
		lcs := make([][]int, len(mx)+1)
		for i := range lcs {
			lcs[i] = make([]int, len(my)+1)
		}
		for i := len(mx) - 1; i >= 0; i-- {
			for j := len(my) - 1; j >= 0; j-- {
				if mx[i] == my[j] {
					lcs[i][j] = lcs[i+1][j+1] + 1
				} else {
					lcs[i][j] = max(lcs[i+1][j], lcs[i][j+1])
				}
			}
		}
		i, j := 0, 0
		for i < len(mx) || j < len(my) {
			switch {
			case i < len(mx) && j < len(my) && mx[i] == my[j]:
				add('=', mx[i:i+1])
				i, j = i+1, j+1
			case i < len(mx) && (j == len(my) || lcs[i+1][j] >= lcs[i][j+1]):
				add('-', mx[i:i+1])
				i++
			default:
				add('+', my[j:j+1])
				j++
			}
		}
	}
	add('=', x[len(x)-suf:])
	return ops
}

func tokenize(s string) []string {
	var toks []string
	start, space := 0, false
	for i, r := range s {
		sp := unicode.IsSpace(r)
		if i > 0 && sp != space {
			toks = append(toks, s[start:i])
			start = i
		}
		space = sp
	}
	if start < len(s) {
		toks = append(toks, s[start:])
	}
	return toks
}

// editOld returns the text an fs_edit call replaces: its `old` argument, or
// the anchored lines read from the file. ok is false when neither resolves.
func editOld(cwd string, args map[string]any) (string, bool) {
	if old, ok := args["old"].(string); ok {
		return old, true
	}
	anchor, _ := args["anchor"].(string)
	path, _ := args["path"].(string)
	if anchor == "" || path == "" {
		return "", false
	}
	if !filepath.IsAbs(path) {
		path = filepath.Join(cwd, path)
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", false
	}
	segs := strings.Split(string(raw), "\n")
	start := findAnchor(segs, anchor)
	end := start
	if endAnchor, _ := args["end_anchor"].(string); endAnchor != "" {
		end = findAnchor(segs, endAnchor)
	}
	if start < 0 || end < start {
		return "", false
	}
	return strings.Join(segs[start:end+1], "\n"), true
}

// findAnchor returns the index of the one line whose anchor matches, else -1.
func findAnchor(segs []string, anchor string) int {
	hit := -1
	for i, seg := range segs {
		if lineAnchor(seg) == anchor {
			if hit >= 0 {
				return -1
			}
			hit = i
		}
	}
	return hit
}

// lineAnchor matches the server's hashline anchor: the first 8 hex of the line's SHA-256.
func lineAnchor(line string) string {
	sum := sha256.Sum256([]byte(line))
	return hex.EncodeToString(sum[:])[:8]
}
