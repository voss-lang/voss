package main

import (
	"fmt"
	"os"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"

	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
)

// Copied from voss/harness/tui/widgets/turn_view.py.
const (
	// transcriptInset is the columns Textual's transcript does not use for
	// text: one column of padding on each side and a two-column scrollbar gutter.
	transcriptInset = 4
	emptyHeading    = "type a message below to begin · / for commands"
	resumeTaskChars = 40
)

var vossLogo = []string{
	`__      ______   _____ _____`,
	`\ \    / / __ \ / ____/ ____|`,
	` \ \  / / |  | | (___| (___`,
	`  \ \/ /| |  | |\___ \\___ \`,
	`   \  / | |__| |____) |___) |`,
	`    \/   \____/|_____/_____/`,
}

// center matches turn_view._center: left padding only, by code points.
func center(line string, width int) string {
	n := utf8.RuneCountInString(line)
	if width <= n {
		return line
	}
	return strings.Repeat(" ", (width-n)/2) + line
}

// relativeAge matches turn_view._relative_age.
func relativeAge(iso string, now time.Time) string {
	var ts time.Time
	var err error
	for _, layout := range []string{time.RFC3339Nano, "2006-01-02T15:04:05.999999999"} {
		if ts, err = time.Parse(layout, iso); err == nil {
			break
		}
	}
	if err != nil {
		return ""
	}
	seconds := max(0, int(now.Sub(ts).Seconds()))
	switch {
	case seconds < 60:
		return "just now"
	case seconds < 3600:
		return fmt.Sprintf("%dm ago", seconds/60)
	case seconds < 86400:
		return fmt.Sprintf("%dh ago", seconds/3600)
	}
	return fmt.Sprintf("%dd ago", seconds/86400)
}

// resumeRow is the newest saved session other than the current one, as
// `⎇ <id6> "<first task>" · <age>`, or "" when there is none.
func resumeRow(cwd, currentID string, now time.Time) string {
	for _, r := range readSavedRecords(cwd) {
		if r.Id == currentID {
			continue
		}
		task := r.firstTask()
		if runes := []rune(task); len(runes) > resumeTaskChars {
			task = string(runes[:resumeTaskChars-1]) + "…"
		}
		id := []rune(r.Id)
		line := fmt.Sprintf(`%s %s "%s"`, glyphs.Fork, string(id[:min(6, len(id))]), task)
		if age := relativeAge(r.UpdatedAt, now); age != "" {
			line += " · " + age
		}
		return line
	}
	return ""
}

// homeRows are the cwd, model and resume rows, each left out when empty.
func homeRows(meta sessionMeta) [][2]string {
	var rows [][2]string
	if meta.Cwd != "" {
		cwd := meta.Cwd
		if home, err := os.UserHomeDir(); err == nil {
			cwd = strings.Replace(cwd, home, "~", 1)
		}
		if meta.Git != "" {
			cwd += "  (" + meta.Git + ")"
		}
		rows = append(rows, [2]string{"cwd", cwd})
	}
	pm := meta.Provider + meta.Model
	if meta.Provider != "" && meta.Model != "" {
		pm = meta.Provider + " / " + meta.Model
	}
	if pm != "" {
		rows = append(rows, [2]string{"model", pm})
	}
	if meta.Resume != "" {
		rows = append(rows, [2]string{"resume", meta.Resume})
	}
	return rows
}

// homeScreen draws Textual's empty-state splash for a terminal of the given
// size. Lines are centred on the full width and wrapped to the transcript's
// width, as the Textual widget is.
func homeScreen(width, height int, rows [][2]string) string {
	width, height = max(40, width), max(12, height)
	logo := lipgloss.NewStyle().Foreground(col(palette.Accent)).Bold(true)
	faint := lipgloss.NewStyle().Faint(true)
	type line struct {
		text  string
		style lipgloss.Style
	}
	var lines []line
	for range max(1, min(4, height/8)) {
		lines = append(lines, line{"", faint})
	}
	if width >= 70 {
		for _, l := range vossLogo {
			lines = append(lines, line{center(l, width), logo})
		}
	} else {
		lines = append(lines, line{center("VOSS", width), logo})
	}
	lines = append(lines, line{center("v1", width), faint}, line{"", faint})
	if len(rows) > 0 {
		longest := 0
		texts := make([]string, len(rows))
		for i, r := range rows {
			texts[i] = fmt.Sprintf("%-9s%s", r[0], r[1])
			longest = max(longest, utf8.RuneCountInString(texts[i]))
		}
		pad := strings.Repeat(" ", max(0, (width-longest)/2))
		for _, t := range texts {
			lines = append(lines, line{pad + t, faint})
		}
		lines = append(lines, line{"", faint})
	}
	lines = append(lines, line{center(emptyHeading, width), faint})

	var out []string
	for _, l := range lines {
		for _, w := range richWrap(l.text, width-transcriptInset) {
			if w == "" {
				out = append(out, "")
				continue
			}
			out = append(out, l.style.Render(w))
		}
	}
	return strings.Join(out, "\n")
}

var richWord = regexp.MustCompile(`\s*\S+\s*`)

// richWrap follows Rich's divide_line: a word that does not fit starts a new
// line, and a word wider than the line is chopped into width-sized pieces.
func richWrap(text string, width int) []string {
	if strings.TrimSpace(text) == "" || width <= 0 {
		return []string{text}
	}
	var lines []string
	line, pos := "", 0
	flush := func() {
		lines = append(lines, strings.TrimRight(line, " "))
		line, pos = "", 0
	}
	for _, word := range richWord.FindAllString(text, -1) {
		wordLen := ansi.StringWidth(strings.TrimRight(word, " "))
		switch {
		case width-pos >= wordLen:
		case wordLen > width:
			if pos > 0 {
				flush()
			}
			for ansi.StringWidth(word) > width {
				line = ansi.Truncate(word, width, "")
				word = ansi.TruncateLeft(word, width, "")
				flush()
			}
		default:
			flush()
		}
		line += word
		pos += ansi.StringWidth(word)
	}
	if line != "" {
		flush()
	}
	return lines
}
