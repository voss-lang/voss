package main

import (
	"fmt"
	"math"
	"reflect"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

// Tool cards, ported from voss/harness/tui/widgets/tool_card.py: one card per
// call that turns from running into ok or error in place.

const (
	outputTailLines = 20
	errorHeadLines  = 10
	maxDiffHunks    = 3
	hunkSideLines   = 4
)

var (
	readTools  = map[string]bool{"fs_read": true, "fs_read_many": true}
	editTools  = map[string]bool{"fs_edit": true, "fs_edit_many": true, "fs_write": true}
	shellTools = map[string]bool{"shell_run": true, "shell_run_background": true}
	matchTools = map[string]bool{"fs_grep": true, "fs_glob": true, "code_search": true, "find_references": true}
	exitRE     = regexp.MustCompile(`^\[exit (-?\d+)\]`)
	deltaRE    = regexp.MustCompile(`\(([+-]\d+) lines`)
)

type toolCard struct {
	name     string
	args     map[string]any
	state    string // running, ok or error
	summary  string
	output   string // the server sends no output yet, so this is the summary
	started  time.Time
	elapsed  time.Duration
	expanded bool
	frame0   int // the model's spinner frame when the card opened
}

// matchCard finds the running card a settled event belongs to: the oldest one
// with the same tool name and arguments, or -1. The server drops call_id, so
// two identical calls running at once can swap results.
func (m chatModel) matchCard(ev voss.ToolEvent) int {
	for i, b := range m.blocks {
		if c := b.card; c != nil && c.state == "running" && c.name == ev.Name && reflect.DeepEqual(c.args, argsOf(ev)) {
			return i
		}
	}
	return -1
}

func argsOf(ev voss.ToolEvent) map[string]any {
	if ev.Args == nil {
		return map[string]any{}
	}
	return *ev.Args
}

// toolEvent opens, settles or adds a card, as TextualRenderer.show_tool_call does.
func (m *chatModel) toolEvent(ev voss.ToolEvent) {
	summary := ""
	if ev.Summary != nil {
		summary = *ev.Summary
	}
	if ev.State == "pending" {
		m.add(block{kind: blockTool, joined: true, card: &toolCard{
			name: ev.Name, args: argsOf(ev), state: "running", started: time.Now(), expanded: m.detailExpanded, frame0: m.frame,
		}})
		return
	}
	i := m.matchCard(ev)
	if i < 0 {
		m.add(block{kind: blockTool, joined: true, card: &toolCard{name: ev.Name, args: argsOf(ev), started: time.Now(), expanded: m.detailExpanded}})
		i = len(m.blocks) - 1
	}
	c := m.blocks[i].card
	c.elapsed = time.Since(c.started)
	c.state = "error"
	if ev.State == "ok" {
		c.state = "ok"
	}
	c.summary, c.output = summary, summary
	if c.state == "error" {
		c.expanded = true
	}
	m.rendered[i] = m.renderAt(i)
}

// refreshRunningCards re-renders cards whose spinner and timer are moving.
func (m *chatModel) refreshRunningCards() {
	for i, b := range m.blocks {
		if b.card != nil && b.card.state == "running" {
			m.rendered[i] = m.renderAt(i)
		}
	}
}

// toggleCard expands or collapses one card when it has a body.
func (m *chatModel) toggleCard(i int) {
	c := m.blocks[i].card
	if c == nil {
		return
	}
	if c.expanded {
		c.expanded = false
	} else if c.hasBody() {
		c.expanded = true
	}
	m.rendered[i] = m.renderAt(i)
}

// toggleAllCards is Textual's action_toggle_detail, bound here to Ctrl+O.
func (m *chatModel) toggleAllCards() {
	m.detailExpanded = !m.detailExpanded
	for i, b := range m.blocks {
		if c := b.card; c != nil {
			c.expanded = m.detailExpanded && c.hasBody()
			m.rendered[i] = m.renderAt(i)
		}
	}
}

func fmtDuration(d time.Duration) string {
	s := d.Seconds()
	if s >= 10 {
		return fmt.Sprintf("%.0fs", math.RoundToEven(s))
	}
	return fmt.Sprintf("%.1fs", s)
}

// metric is the right-aligned result per tool class, from tool_card._metric.
func (c toolCard) metric() string {
	duration := fmtDuration(c.elapsed)
	switch {
	case shellTools[c.name]:
		src := c.output
		if src == "" {
			src = c.summary
		}
		if m := exitRE.FindStringSubmatch(src); m != nil {
			return fmt.Sprintf("exit %s · %s", m[1], duration)
		}
	case readTools[c.name]:
		// Needs the full output (S1); the summary is only its first line.
	case matchTools[c.name]:
		// Needs the full output (S1).
	case editTools[c.name]:
		if added, deleted, ok := editCounts(c.name, c.args); ok {
			return fmt.Sprintf("+%d -%d", added, deleted)
		}
		if m := deltaRE.FindStringSubmatch(c.summary); m != nil {
			return m[1] + " lines"
		}
	}
	return duration
}

// splitLines is Python's str.splitlines, with `or [""]` applied by callers.
func splitLines(s string) []string {
	s = strings.ReplaceAll(strings.ReplaceAll(s, "\r\n", "\n"), "\r", "\n")
	lines := strings.Split(s, "\n")
	if len(lines) > 0 && lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	return lines
}

func lineCount(s string) int { return max(len(splitLines(s)), 1) }

func editCounts(name string, args map[string]any) (int, int, bool) {
	switch name {
	case "fs_write":
		if content, ok := args["content"]; ok {
			return lineCount(pyStr(content)), 0, true
		}
	case "fs_edit":
		if old, ok := args["old"]; ok && old != nil {
			if newText, ok := args["new"]; ok {
				return lineCount(pyStr(newText)), lineCount(pyStr(old)), true
			}
		}
	case "fs_edit_many":
		edits, ok := args["edits"].([]any)
		if !ok {
			break
		}
		added, deleted := 0, 0
		for _, e := range edits {
			edit, ok := e.(map[string]any)
			if !ok {
				return 0, 0, false
			}
			added += lineCount(pyStr(orEmpty(edit["new"])))
			deleted += lineCount(pyStr(orEmpty(edit["old"])))
		}
		return added, deleted, true
	}
	return 0, 0, false
}

func orEmpty(v any) any {
	if v == nil {
		return ""
	}
	return v
}

type hunk struct{ old, new []string }

func orBlank(lines []string) []string {
	if len(lines) == 0 {
		return []string{""}
	}
	return lines
}

// diffHunks rebuilds the mini diff from the call arguments; anchor edits have none.
func diffHunks(name string, args map[string]any) []hunk {
	switch name {
	case "fs_edit":
		if old, ok := args["old"]; ok && old != nil {
			if newText, ok := args["new"]; ok {
				return []hunk{{orBlank(splitLines(pyStr(old))), orBlank(splitLines(pyStr(newText)))}}
			}
		}
	case "fs_edit_many":
		edits, ok := args["edits"].([]any)
		if !ok {
			break
		}
		var hunks []hunk
		for _, e := range edits[:min(len(edits), maxDiffHunks)] {
			if edit, ok := e.(map[string]any); ok {
				hunks = append(hunks, hunk{orBlank(splitLines(pyStr(orEmpty(edit["old"])))), orBlank(splitLines(pyStr(orEmpty(edit["new"]))))})
			}
		}
		return hunks
	}
	return nil
}

func (c toolCard) hasBody() bool {
	if c.state == "running" {
		return false
	}
	return strings.TrimSpace(c.output) != "" || len(diffHunks(c.name, c.args)) > 0
}

// argSummary is ", ".join(f"{k}={_short(v, limit)}"), with keys sorted
// because the arguments arrive as a Go map.
func argSummary(args map[string]any, limit int) string {
	keys := make([]string, 0, len(args))
	for k := range args {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	parts := make([]string, len(keys))
	for i, k := range keys {
		parts[i] = k + "=" + short(pyStr(args[k]), limit)
	}
	return strings.Join(parts, ", ")
}

// pyStr formats a JSON value the way Python's str() does.
func pyStr(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return pyRepr(v)
}

func pyRepr(v any) string {
	switch v := v.(type) {
	case nil:
		return "None"
	case bool:
		if v {
			return "True"
		}
		return "False"
	case float64:
		if v == math.Trunc(v) && math.Abs(v) < 1e16 {
			return strconv.FormatInt(int64(v), 10)
		}
		return strconv.FormatFloat(v, 'g', -1, 64)
	case string:
		if strings.Contains(v, "'") && !strings.Contains(v, `"`) {
			return `"` + v + `"`
		}
		esc := strings.NewReplacer(`\`, `\\`, "\n", `\n`, "\t", `\t`, "\r", `\r`, "'", `\'`)
		return "'" + esc.Replace(v) + "'"
	case []any:
		parts := make([]string, len(v))
		for i, x := range v {
			parts[i] = pyRepr(x)
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case map[string]any:
		keys := make([]string, 0, len(v))
		for k := range v {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		parts := make([]string, len(keys))
		for i, k := range keys {
			parts[i] = pyRepr(k) + ": " + pyRepr(v[k])
		}
		return "{" + strings.Join(parts, ", ") + "}"
	}
	return fmt.Sprint(v)
}

// toolCard renders a card: the head, then the expander and body once settled.
func (r renderer) toolCard(c *toolCard, frame int) string {
	faint := lipgloss.NewStyle().Faint(true)
	var left, right string
	var more []string // argument values with newlines continue the head, as in Textual
	if c.state == "running" {
		frames := []rune(glyphs.SpinnerFrames)
		left = faint.Render(string(frames[max(frame-c.frame0, 0)%len(frames)]) + " " + c.name)
		right = faint.Render(fmtDuration(time.Since(c.started)))
	} else {
		colour := palette.Good
		if c.state == "error" {
			colour = palette.Error
		}
		left = lipgloss.NewStyle().Foreground(col(colour)).Render(glyphs.ToolOk) + " " + c.name
		right = faint.Render(c.metric())
	}
	if args := argSummary(c.args, 40); args != "" {
		argLines := strings.Split(" "+args, "\n")
		left += faint.Render(argLines[0])
		for _, l := range argLines[1:] {
			more = append(more, faint.Render(ansi.Truncate(l, max(r.width, 1), "…")))
		}
	}
	room := max(r.width-ansi.StringWidth(right)-1, 1)
	left = ansi.Truncate(left, room, "…")
	head := strings.Join(append([]string{left + strings.Repeat(" ", max(room-ansi.StringWidth(left), 0)+1) + right}, more...), "\n")
	if c.state == "running" || !c.hasBody() {
		return head
	}
	lines := []string{head, faint.Render(c.expander())}
	if c.expanded {
		lines = append(lines, c.bodyLines(r.width)...)
	}
	return strings.Join(lines, "\n")
}

func (c toolCard) expander() string {
	chevron := glyphs.ChevronClosed
	if c.expanded {
		chevron = glyphs.ChevronOpen
	}
	line := glyphs.OutputElbow + " " + chevron
	if !c.expanded {
		if n := len(diffHunks(c.name, c.args)); n > 0 {
			plural := "s"
			if n == 1 {
				plural = ""
			}
			line += fmt.Sprintf(" %d hunk%s · ctrl+d full diff", n, plural)
		} else {
			line += " …"
		}
	}
	return line
}

// bodyLines is the expanded body: full arguments, then the mini diff for
// edits or an excerpt of the output.
func (c toolCard) bodyLines(width int) []string {
	faint := lipgloss.NewStyle().Faint(true)
	good := lipgloss.NewStyle().Foreground(col(palette.Good))
	bad := lipgloss.NewStyle().Foreground(col(palette.Error))
	var lines []string
	add := func(text string, st lipgloss.Style) {
		for _, w := range richWrap(text, width) {
			lines = append(lines, st.Render(w))
		}
	}
	if len(c.args) > 0 {
		add("   "+argSummary(c.args, 120), faint)
	}
	if hunks := diffHunks(c.name, c.args); len(hunks) > 0 {
		for _, h := range hunks {
			for _, l := range h.old[:min(len(h.old), hunkSideLines)] {
				add("   - "+l, bad)
			}
			if len(h.old) > hunkSideLines {
				add("   - …", bad)
			}
			for _, l := range h.new[:min(len(h.new), hunkSideLines)] {
				add("   + "+l, good)
			}
			if len(h.new) > hunkSideLines {
				add("   + …", good)
			}
		}
		return lines
	}
	out := splitLines(c.output)
	excerpt, truncated := out, false
	if c.state == "error" {
		truncated = len(out) > errorHeadLines
		excerpt = out[:min(len(out), errorHeadLines)]
	} else {
		truncated = len(out) > outputTailLines
		excerpt = out[max(len(out)-outputTailLines, 0):]
	}
	if truncated {
		add("   …", faint)
	}
	for _, l := range excerpt {
		add("   "+l, faint)
	}
	return lines
}

// plainText is the card as tool_card.plain_text flattens it, for nav-mode y.
func (c toolCard) plainText() string {
	var parts []string
	if c.state == "running" {
		parts = []string{strings.TrimRight(string([]rune(glyphs.SpinnerFrames)[0])+" "+c.name+" "+argSummary(c.args, 40), " ")}
	} else {
		head := glyphs.ToolOk + " " + c.name
		if a := argSummary(c.args, 40); a != "" {
			head += " " + a
		}
		parts = []string{head + "  " + c.metric()}
	}
	if c.state != "running" && c.hasBody() {
		parts = append(parts, c.expander())
		if c.expanded {
			for _, l := range c.bodyLines(1 << 30) {
				parts = append(parts, ansi.Strip(l))
			}
		}
	}
	return strings.Join(parts, "\n")
}
