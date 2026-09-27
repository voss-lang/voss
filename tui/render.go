package main

import (
	"errors"
	"fmt"
	"math"
	"sort"
	"strings"

	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

var (
	styleUser    = lipgloss.NewStyle().Bold(true)
	styleDim     = lipgloss.NewStyle().Faint(true)
	styleTool    = lipgloss.NewStyle().Foreground(lipgloss.Yellow)
	styleClarify = lipgloss.NewStyle().Foreground(lipgloss.Cyan)
	styleError   = lipgloss.NewStyle().Foreground(lipgloss.Red)
	styleDel     = lipgloss.NewStyle().Foreground(lipgloss.Red).Strikethrough(true)
	styleAdd     = lipgloss.NewStyle().Foreground(lipgloss.Green)
)

const (
	defaultWidth = 80
	maxDiffLines = 20
)

// renderer draws blocks for one transcript width.
type renderer struct {
	width int
}

func newRenderer(width int) renderer {
	if width <= 0 {
		width = defaultWidth
	}
	return renderer{width: width}
}

func (r renderer) block(b block) string {
	switch b.kind {
	case blockUser:
		return r.user(b.text)
	case blockAssistant:
		return r.assistant(b.text, b.footer)
	case blockRole:
		return r.role(b.role, b.text)
	case blockConfidence:
		return confidenceBar(b.conf, false)
	case blockTool:
		return styleTool.Render(ansi.Truncate("⚙ "+b.text, r.width, "…"))
	case blockToolArgs:
		lines := strings.Split(b.text, "\n")
		for i, line := range lines {
			lines[i] = styleDim.Render(ansi.Truncate(line, r.width, "…"))
		}
		return strings.Join(lines, "\n")
	}
	return b.text
}

// user draws Textual's UserBlock: a faint accent edge, one column of padding
// and faint text on the surface colour, filling the width.
func (r renderer) user(text string) string {
	edge := lipgloss.NewStyle().Foreground(blend(palette.Accent, palette.Bg, 0.06)).Background(col(palette.Surface)).Render("▎")
	fill := lipgloss.NewStyle().Background(col(palette.Surface))
	body := fill.Faint(true).Foreground(col(userText))
	textW := max(r.width-3, 1)
	var out []string
	for i, line := range strings.Split(text, "\n") {
		prefix := "  "
		if i == 0 {
			prefix = glyphs.UserInput + " "
		}
		for _, w := range richWrap(prefix+line, textW) {
			out = append(out, edge+fill.Render(" ")+body.Render(w)+fill.Render(strings.Repeat(" ", max(textW-ansi.StringWidth(w), 0)+1)))
		}
	}
	return strings.Join(out, "\n")
}

// assistant draws Textual's AssistantBlock: a bold accent gutter, the
// markdown body, and the faint metadata footer when there is one.
func (r renderer) assistant(text, footer string) string {
	gutter := lipgloss.NewStyle().Foreground(col(palette.Accent)).Bold(true).Render(glyphs.Assistant)
	lines := strings.Split(richMarkdown(text, r.width-2), "\n")
	for i, line := range lines {
		if i == 0 {
			lines[i] = gutter + " " + line
		} else {
			lines[i] = "  " + line
		}
	}
	if footer != "" {
		for _, w := range richWrap(footer, r.width) {
			lines = append(lines, lipgloss.NewStyle().Faint(true).Render(w))
		}
	}
	return strings.Join(lines, "\n")
}

// role draws Textual's RoleBlock: a faint label, then the body indented two
// columns.
func (r renderer) role(role, text string) string {
	faint := lipgloss.NewStyle().Faint(true)
	out := []string{faint.Render(role)}
	for _, line := range strings.Split(text, "\n") {
		for _, w := range richWrap("  "+line, r.width) {
			out = append(out, faint.Render(w))
		}
	}
	return strings.Join(out, "\n")
}

// confidenceBar matches Textual's ConfidenceBar: ten cells, the value, and a
// colour by threshold.
func confidenceBar(value float64, final bool) string {
	value = math.Max(0, math.Min(1, value))
	filled := int(math.RoundToEven(value * 10))
	colour := palette.Error
	switch {
	case final && value >= 0.85:
		colour = palette.Accent
	case value >= 0.85:
		colour = palette.Good
	case value >= 0.5:
		colour = palette.Warn
	}
	bar := strings.Repeat(glyphs.BarFill, filled) + strings.Repeat(glyphs.BarEmpty, 10-filled)
	return lipgloss.NewStyle().Foreground(col(colour)).Render(fmt.Sprintf("%s %.2f ", bar, value))
}

// hang wraps text to the width with a glyph on the first line and a
// two-column indent on the rest.
func (r renderer) hang(glyph, text string, style lipgloss.Style) string {
	indent := ""
	if glyph != "" {
		indent = "  "
	}
	lines := strings.Split(ansi.Wrap(text, r.width-len(indent), ""), "\n")
	for i, line := range lines {
		prefix := indent
		if i == 0 && glyph != "" {
			prefix = glyph + " "
		}
		lines[i] = style.Render(prefix + line)
	}
	return strings.Join(lines, "\n")
}

func (r renderer) permission(p voss.PermissionUpdated, cwd string) string {
	var args map[string]any
	if p.Args != nil {
		args = *p.Args
	}
	if p.ToolName == "scope_expand" {
		return styleTool.Render(fmt.Sprintf("⚠ expand scope to %v?", args["target"])) + "  [y] yes  [n] no"
	}
	head := styleTool.Render("⚠ allow " + p.ToolName + "?")
	var body string
	switch p.ToolName {
	case "fs_edit":
		head += " " + styleDim.Render(fmt.Sprint(args["path"]))
		newText, _ := args["new"].(string)
		old, ok := editOld(cwd, args)
		body = r.diff(old, newText, ok)
	case "fs_edit_many":
		head += " " + styleDim.Render(fmt.Sprint(args["path"]))
		edits, _ := args["edits"].([]any)
		parts := make([]string, 0, len(edits))
		for _, e := range edits {
			edit, _ := e.(map[string]any)
			old, ok := edit["old"].(string)
			newText, _ := edit["new"].(string)
			parts = append(parts, r.diff(old, newText, ok))
		}
		body = strings.Join(parts, "\n"+styleDim.Render("  ···")+"\n")
	default:
		head = r.hang("", head+" "+styleDim.Render(argSummary(args)), lipgloss.NewStyle())
	}
	out := head
	if body != "" {
		out += "\n" + body
	}
	return out + "\n  [a] allow once  [A] always  [d] deny"
}

// diff renders old -> new as an indented word diff, or new alone when the old
// text could not be found.
func (r renderer) diff(old, newText string, haveOld bool) string {
	var sb strings.Builder
	if !haveOld {
		sb.WriteString(styleDim.Render("(old text unavailable)") + "\n")
		writeStyled(&sb, newText, styleAdd)
	} else {
		for _, op := range wordDiff(old, newText) {
			switch op.kind {
			case '-':
				writeStyled(&sb, op.text, styleDel)
			case '+':
				writeStyled(&sb, op.text, styleAdd)
			default:
				sb.WriteString(op.text)
			}
		}
	}
	lines := strings.Split(ansi.Wrap(sb.String(), r.width-2, ""), "\n")
	extra := len(lines) - maxDiffLines
	if extra > 0 {
		lines = lines[:maxDiffLines]
	}
	for i, line := range lines {
		lines[i] = "  " + line
	}
	if extra > 0 {
		lines = append(lines, styleDim.Render(fmt.Sprintf("  … %d more lines", extra)))
	}
	return strings.Join(lines, "\n")
}

// writeStyled styles each line separately so the styling never spans a newline.
func writeStyled(sb *strings.Builder, text string, style lipgloss.Style) {
	for i, line := range strings.Split(text, "\n") {
		if i > 0 {
			sb.WriteByte('\n')
		}
		if line != "" {
			sb.WriteString(style.Render(line))
		}
	}
}

// toolArgsText lists a tool call's arguments one per line.
func toolArgsText(ev voss.ToolEvent) string {
	lines := []string{ev.Name + " arguments:"}
	if ev.Args == nil || len(*ev.Args) == 0 {
		lines = append(lines, "  (none)")
	}
	if ev.Args != nil {
		for _, k := range sortedKeys(*ev.Args) {
			lines = append(lines, "  "+k+": "+strings.ReplaceAll(fmt.Sprint((*ev.Args)[k]), "\n", "⏎"))
		}
	}
	return strings.Join(lines, "\n")
}

func argSummary(args map[string]any) string {
	pairs := make([]string, 0, len(args))
	for _, k := range sortedKeys(args) {
		pairs = append(pairs, k+"="+short(strings.ReplaceAll(fmt.Sprint(args[k]), "\n", "⏎"), 60))
	}
	return strings.Join(pairs, " ")
}

func sortedKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func errText(err error) string {
	var ve *voss.VossError
	if errors.As(err, &ve) && ve.Detail != "" {
		return ve.Detail
	}
	return err.Error()
}

func short(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n-1]) + "…"
}
