package main

import (
	"errors"
	"fmt"
	"sort"
	"strings"

	"charm.land/glamour/v2"
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

// renderer draws blocks for one terminal width and background.
type renderer struct {
	width int
	md    *glamour.TermRenderer
}

// newRenderer always uses glamour's dark style: like Textual, the client
// paints its own dark background.
func newRenderer(width int) renderer {
	if width <= 0 {
		width = defaultWidth
	}
	// glamour's styles add a 2-column margin on each side of the wrapped text.
	md, err := glamour.NewTermRenderer(glamour.WithStandardStyle("dark"), glamour.WithWordWrap(max(width-4, 20)))
	if err != nil {
		md = nil
	}
	return renderer{width: width, md: md}
}

func (r renderer) markdown(s string) string {
	if r.md == nil {
		return s
	}
	out, err := r.md.Render(s)
	if err != nil {
		return s
	}
	lines := strings.Split(out, "\n")
	for i, line := range lines {
		// glamour pads each line to the wrap width with styled spaces.
		visible := strings.TrimRight(ansi.Strip(line), " ")
		if visible == "" {
			lines[i] = ""
			continue
		}
		lines[i] = ansi.Truncate(line, ansi.StringWidth(visible), "")
	}
	return strings.Trim(strings.Join(lines, "\n"), "\n")
}

func (r renderer) block(b block) string {
	switch b.kind {
	case blockUser:
		return "\n" + r.hang("›", b.text, styleUser)
	case blockAssistant:
		return r.markdown(b.text)
	case blockPlan, blockNotice:
		return r.hang("", b.text, styleDim)
	case blockTool:
		return styleTool.Render(ansi.Truncate("⚙ "+b.text, r.width, "…"))
	case blockClarify:
		return r.hang("?", b.text, styleClarify)
	case blockWarning:
		return r.hang("⚠", b.text, styleTool)
	case blockError:
		return r.hang("✗", b.text, styleError)
	case blockToolArgs:
		lines := strings.Split(b.text, "\n")
		for i, line := range lines {
			lines[i] = styleDim.Render(ansi.Truncate(line, r.width, "…"))
		}
		return strings.Join(lines, "\n")
	}
	return b.text
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
