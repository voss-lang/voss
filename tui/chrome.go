package main

import (
	"context"
	"fmt"
	"image/color"
	"math"
	"os/exec"
	"strconv"
	"strings"
	"time"

	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
)

const ctxCells = 4

// sessionMeta is what the chrome shows about the session before any turn runs.
type sessionMeta struct {
	ID, Cwd, Provider, Model, Git, Resume string
}

func col(c string) color.Color { return lipgloss.Color(c) }

// blend mixes fg over bg at alpha, as Textual does for `$accent 15%`.
func blend(fg, bg string, alpha float64) color.Color {
	channel := func(s string, i int) float64 {
		v, _ := strconv.ParseUint(s[1+2*i:3+2*i], 16, 8)
		return float64(v)
	}
	out := "#"
	for i := range 3 {
		out += fmt.Sprintf("%02x", int(math.Round(channel(bg, i)+(channel(fg, i)-channel(bg, i))*alpha)))
	}
	return lipgloss.Color(out)
}

// providerLabel names the provider behind an auth source, like the CLI's
// _provider_label_for_auth. Unknown sources show as they are.
func providerLabel(auth string) string {
	switch auth {
	case "codex", "codex-oauth":
		return "Codex"
	case "claude-agent", "env-anthropic", "voss-anthropic":
		return "Anthropic"
	case "env-openai", "voss-openai":
		return "OpenAI"
	}
	return auth
}

// gitSummary counts changed files the way the CLI's _git_status does.
func gitSummary(cwd string) string {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "git", "status", "--porcelain")
	cmd.Dir = cwd
	out, err := cmd.Output()
	if err != nil {
		return "not a git repo"
	}
	var plus, mod, minus, total int
	for _, line := range strings.Split(string(out), "\n") {
		if strings.TrimSpace(line) == "" {
			continue
		}
		total++
		switch {
		case strings.HasPrefix(line, "A"), strings.HasPrefix(line, "?"):
			plus++
		case strings.HasPrefix(line, "D"):
			minus++
		}
		if strings.HasPrefix(line, " M") || strings.HasPrefix(line, "M") {
			mod++
		}
	}
	if total == 0 {
		return "clean"
	}
	return fmt.Sprintf("+%d ~%d -%d", plus, mod, minus)
}

// statusLine draws Textual's two-zone status row with a one-column margin.
// The left zone is cut first when the row is too narrow.
func statusLine(width int, provider, model, phase string, ctxPct, cost float64, git string) string {
	dim := lipgloss.NewStyle().Foreground(col(palette.Dim))
	text := lipgloss.NewStyle().Foreground(col(palette.Text))
	sep := dim.Render(" · ")

	left := lipgloss.NewStyle().Foreground(col(palette.Accent)).Bold(true).Render(glyphs.Prompt + " voss")
	pm := provider
	if provider != "" && model != "" {
		pm = provider + " / " + model
	} else if model != "" {
		pm = model
	}
	if pm != "" {
		left += sep + text.Render(pm)
	}
	if phase != "" {
		left += sep + dim.Render(phase)
	}

	pct := math.Max(0, ctxPct)
	filled := min(ctxCells, int(math.RoundToEven(math.Min(pct, 1)*ctxCells)))
	barColor := palette.Dim
	if pct >= 1 {
		barColor = palette.Error
	} else if pct >= 0.75 {
		barColor = palette.Warn
	}
	bar := strings.Repeat(glyphs.BudgetFill, filled) + strings.Repeat(glyphs.BudgetEmpty, ctxCells-filled)
	right := lipgloss.NewStyle().Foreground(col(barColor)).Render(fmt.Sprintf("%s %.0f%%", bar, pct*100))
	costColor := palette.Text
	if cost > 1 {
		costColor = palette.Error
	}
	right += sep + lipgloss.NewStyle().Foreground(col(costColor)).Render(fmt.Sprintf("$%.2f", cost))
	if git != "" {
		right += sep + dim.Render(git)
	}

	inner := max(width-2, 0)
	right = ansi.Truncate(right, inner, "")
	room := inner - ansi.StringWidth(right)
	left = ansi.Truncate(left, room, "…")
	gap := strings.Repeat(" ", max(room-ansi.StringWidth(left), 0))
	return " " + left + gap + right + " "
}

// inputBox frames the editor like Textual's InputBar: a rounded border that
// turns accent when focused, a three-column prompt cell, and the surface fill.
func inputBox(width int, editor string, focused bool) string {
	border := palette.Dim
	cellBg := col(palette.Surface)
	if focused {
		border = palette.Accent
		cellBg = blend(palette.Accent, palette.Surface, 0.15)
	}
	lines := strings.Split(editor, "\n")
	cell := lipgloss.NewStyle().Background(cellBg).Foreground(col(palette.Accent)).Bold(true)
	blank := lipgloss.NewStyle().Background(cellBg)
	fill := lipgloss.NewStyle().Background(col(palette.Surface))
	inner := max(width-4, 4)
	for i, line := range lines {
		prompt := blank.Render("   ")
		if i == 0 {
			prompt = cell.Render(glyphs.Prompt) + blank.Render("  ")
		}
		pad := max(inner-3-ansi.StringWidth(line), 0)
		lines[i] = prompt + line + fill.Render(strings.Repeat(" ", pad))
	}
	box := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(col(border)).
		BorderBackground(col(palette.Surface)).
		Render(strings.Join(lines, "\n"))
	return lipgloss.NewStyle().Padding(0, 1).Render(box)
}

// workingLine is Textual's WorkingIndicator: the brand glyph until the first
// spinner tick, then spinner frames.
func workingLine(frame int, label string, elapsed time.Duration, tokens int) string {
	glyph := glyphs.Working
	if frame >= 0 {
		frames := []rune(glyphs.SpinnerFrames)
		glyph = string(frames[frame%len(frames)])
	}
	out := fmt.Sprintf("%s %s · %ds", glyph, label, int(elapsed.Seconds()))
	if tokens > 0 {
		if tokens >= 1000 {
			out += fmt.Sprintf(" · %.1fk tok", float64(tokens)/1000)
		} else {
			out += fmt.Sprintf(" · %d tok", tokens)
		}
	}
	return lipgloss.NewStyle().Faint(true).Render(out + " · ctrl+c to interrupt")
}
