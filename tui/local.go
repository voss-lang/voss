package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	tea "charm.land/bubbletea/v2"
)

// Input-bar shortcuts that never reach the model: `!cmd` runs a local command
// under the sandbox rules and `#note` appends to VOSS.md. Both follow
// voss/harness/tui/widgets/input_bar.py, sandbox.py and voss_md.py.

var (
	shellAllowlist = map[string]bool{
		"ls": true, "cat": true, "head": true, "tail": true, "grep": true, "rg": true, "find": true, "wc": true,
		"git": true, "pytest": true, "python": true, "python3": true, "voss": true, "npm": true, "node": true,
		"echo": true, "pwd": true, "which": true,
	}
	denyTokens      = []string{"rm -rf", "sudo", "curl http", "nc ", " > /", "shutdown", "reboot", "mkfs"}
	shellMetachars  = []string{";", "|", "&&", "||", "&", "$(", "`", ">", "<", ">>", "<<", "<(", ">("}
	errUnparseable  = errors.New("No closing quotation")
	errNoEscapedEnd = errors.New("No escaped character")
)

// shellAllowed matches sandbox.shell_allowed, reasons included.
func shellAllowed(cmd string) (bool, string) {
	lowered := strings.ToLower(cmd)
	for _, bad := range denyTokens {
		if strings.Contains(lowered, bad) {
			return false, fmt.Sprintf("denied token: '%s'", bad)
		}
	}
	for _, meta := range shellMetachars {
		if strings.Contains(cmd, meta) {
			return false, fmt.Sprintf("shell metacharacter not allowed: '%s'", meta)
		}
	}
	parts, err := shlexSplit(cmd)
	if err != nil {
		return false, "unparseable: " + err.Error()
	}
	if len(parts) == 0 {
		return false, "empty command"
	}
	binary := strings.ToLower(filepath.Base(parts[0]))
	if !shellAllowlist[binary] {
		return false, "binary not in allowlist: " + binary
	}
	return true, "ok"
}

// shlexSplit is Python's shlex.split in POSIX mode: whitespace separates
// words, quotes group, and a backslash escapes outside single quotes.
func shlexSplit(s string) ([]string, error) {
	var words []string
	var cur strings.Builder
	inWord, quote := false, rune(0)
	runes := []rune(s)
	for i := 0; i < len(runes); i++ {
		r := runes[i]
		switch {
		case quote == '\'':
			if r == '\'' {
				quote = 0
			} else {
				cur.WriteRune(r)
			}
		case quote == '"':
			switch {
			case r == '"':
				quote = 0
			case r == '\\' && i+1 < len(runes) && (runes[i+1] == '"' || runes[i+1] == '\\'):
				i++
				cur.WriteRune(runes[i])
			default:
				cur.WriteRune(r)
			}
		case r == '\'' || r == '"':
			quote, inWord = r, true
		case r == '\\':
			if i+1 >= len(runes) {
				return nil, errNoEscapedEnd
			}
			i++
			cur.WriteRune(runes[i])
			inWord = true
		case r == ' ' || r == '\t' || r == '\n' || r == '\r':
			if inWord {
				words = append(words, cur.String())
				cur.Reset()
				inWord = false
			}
		default:
			cur.WriteRune(r)
			inWord = true
		}
	}
	if quote != 0 {
		return nil, errUnparseable
	}
	if inWord {
		words = append(words, cur.String())
	}
	return words, nil
}

type shellDoneMsg struct {
	cmd, stdout, stderr string
	exit                int
}

// runShell runs an allowed command in cwd without a shell, as Textual does.
func runShell(ctx context.Context, cwd, cmd string) tea.Cmd {
	return func() tea.Msg {
		if ok, reason := shellAllowed(cmd); !ok {
			return shellDoneMsg{cmd: cmd, stdout: reason, exit: 1}
		}
		argv, _ := shlexSplit(cmd)
		c := exec.CommandContext(ctx, argv[0], argv[1:]...)
		c.Dir = cwd
		var stdout, stderr strings.Builder
		c.Stdout, c.Stderr = &stdout, &stderr
		exit := 0
		if err := c.Run(); err != nil {
			var ee *exec.ExitError
			if errors.As(err, &ee) {
				exit = ee.ExitCode()
			} else {
				stderr.WriteString(err.Error())
				exit = 1
			}
		}
		return shellDoneMsg{cmd, stdout.String(), stderr.String(), exit}
	}
}

// VOSS.md notes, ported from voss_md.parse, _render and append_voss_notes_bullet.

var (
	fenceBegin = regexp.MustCompile(`^<!-- voss:begin id=([\w-]+) -->`)
	fenceHash  = regexp.MustCompile(`^<!-- voss:hash ([0-9a-f]{64}) -->`)
	fenceEnd   = regexp.MustCompile(`^<!-- voss:end id=([\w-]+) -->`)
)

type mdBlock struct {
	machine        bool
	id, body, hash string
}

func splitLinesKeepEnds(text string) []string {
	var lines []string
	for text != "" {
		i := strings.IndexByte(text, '\n')
		if i < 0 {
			lines = append(lines, text)
			break
		}
		lines = append(lines, text[:i+1])
		text = text[i+1:]
	}
	return lines
}

func parseVossMD(text string) []mdBlock {
	var blocks []mdBlock
	lines := splitLinesKeepEnds(text)
	for i := 0; i < len(lines); {
		m := fenceBegin.FindStringSubmatch(strings.TrimSpace(lines[i]))
		if m == nil {
			start := i
			for i < len(lines) && !fenceBegin.MatchString(strings.TrimSpace(lines[i])) {
				i++
			}
			if body := strings.Join(lines[start:i], ""); body != "" {
				blocks = append(blocks, mdBlock{body: body})
			}
			continue
		}
		id, hash := m[1], ""
		bodyStart := i + 1
		if bodyStart < len(lines) {
			if h := fenceHash.FindStringSubmatch(strings.TrimSpace(lines[bodyStart])); h != nil {
				hash = h[1]
				bodyStart++
			}
		}
		j := bodyStart
		for j < len(lines) {
			if e := fenceEnd.FindStringSubmatch(strings.TrimSpace(lines[j])); e != nil && e[1] == id {
				break
			}
			j++
		}
		blocks = append(blocks, mdBlock{machine: true, id: id, body: strings.Join(lines[bodyStart:min(j, len(lines))], ""), hash: hash})
		i = j + 1
	}
	return blocks
}

func renderVossMD(blocks []mdBlock) string {
	var sb strings.Builder
	for _, b := range blocks {
		if !b.machine {
			sb.WriteString(b.body)
			continue
		}
		body := b.body
		if body != "" && !strings.HasSuffix(body, "\n") {
			body += "\n"
		}
		hash := b.hash
		if hash == "" {
			sum := sha256.Sum256([]byte(b.body))
			hash = hex.EncodeToString(sum[:])
		}
		fmt.Fprintf(&sb, "<!-- voss:begin id=%s -->\n<!-- voss:hash %s -->\n%s<!-- voss:end id=%s -->\n", b.id, hash, body, b.id)
	}
	return sb.String()
}

func appendNotesBullet(body, bullet string) string {
	lines := splitLinesKeepEnds(body)
	notes := -1
	for i, l := range lines {
		if strings.TrimSpace(l) == "## Notes" {
			notes = i
			break
		}
	}
	if notes < 0 {
		if body != "" && !strings.HasSuffix(body, "\n") {
			body += "\n"
		}
		return body + "\n## Notes\n\n" + bullet
	}
	insertAt := len(lines)
	for i := notes + 1; i < len(lines); i++ {
		if strings.HasPrefix(lines[i], "## ") {
			insertAt = i
			break
		}
	}
	prefix, suffix := strings.Join(lines[:insertAt], ""), strings.Join(lines[insertAt:], "")
	if prefix != "" && !strings.HasSuffix(prefix, "\n") {
		prefix += "\n"
	}
	if !strings.HasSuffix(prefix, "\n\n") {
		prefix += "\n"
	}
	return prefix + bullet + suffix
}

// appendVossNote adds "- [timestamp] note" under each human section of
// VOSS.md that has a "## Notes" heading, or adds that section at the end.
func appendVossNote(path, note string, now time.Time) error {
	existing, _ := os.ReadFile(path)
	bullet := fmt.Sprintf("- [%s] %s\n", now.UTC().Format("2006-01-02T15:04:05+00:00"), note)
	blocks := parseVossMD(string(existing))
	replaced := false
	for i, b := range blocks {
		if !b.machine && strings.Contains(b.body, "## Notes") {
			blocks[i].body = appendNotesBullet(b.body, bullet)
			replaced = true
		}
	}
	if !replaced {
		if n := len(blocks); n > 0 && !strings.HasSuffix(blocks[n-1].body, "\n") {
			blocks[n-1].body += "\n"
		}
		blocks = append(blocks, mdBlock{body: "\n## Notes\n\n" + bullet})
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, []byte(renderVossMD(blocks)), 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}
