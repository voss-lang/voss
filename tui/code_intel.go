package main

import (
	"fmt"
	"strings"

	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

type codePanel struct {
	results voss.CodeResults
	view    viewport.Model
}

func (m *chatModel) showCodeResults(results voss.CodeResults) {
	m.code = &codePanel{results: results, view: viewport.New()}
	m.code.resize(m.width, m.height)
}

func (p *codePanel) resize(width, height int) {
	p.view.SetWidth(max(width-4, 1))
	p.view.SetHeight(max(height-5, 1))
	var lines []string
	for _, hit := range p.results.Items {
		location := fmt.Sprintf("%s:%d  %s [%s]", hit.File, hit.Line, hit.Name, hit.Source)
		lines = append(lines, lipgloss.NewStyle().Foreground(col(palette.Accent)).Render(ansi.Wrap(ansi.Strip(location), p.view.Width(), "")))
		if hit.Snippet != "" {
			snippet := strings.ReplaceAll(ansi.Strip(hit.Snippet), "\t", "    ")
			lines = append(lines, lipgloss.NewStyle().Foreground(col(palette.OutputText)).Render(ansi.Wrap(snippet, p.view.Width(), "")))
		}
		lines = append(lines, "")
	}
	if len(lines) == 0 {
		lines = append(lines, "No matches. Try another name or /refresh.")
	}
	p.view.SetContent(strings.Join(lines, "\n"))
}

func (p codePanel) screen(width, height int) string {
	inner := max(width-4, 1)
	line := func(s string) string {
		return "  " + ansi.Truncate(s, inner, "…")
	}
	count := fmt.Sprintf("%d matches", len(p.results.Items))
	if p.results.Truncated {
		count += " · more available; refine the query"
	}
	title := "Code Intel · " + strings.Join(strings.Fields(ansi.Strip(p.results.Query)), " ")
	body := lipgloss.NewStyle().Padding(0, 2).Render(p.view.View())
	screen := strings.Join([]string{
		line(lipgloss.NewStyle().Foreground(col(palette.Accent)).Render(title)), line(styleDim.Render(count)), "", body, "",
		line(styleDim.Render("↑/↓ scroll · PgUp/PgDn page · Esc/Enter close")),
	}, "\n")
	return strings.Join(strings.Split(screen, "\n")[:min(lipgloss.Height(screen), height)], "\n")
}

func (m chatModel) codeKey(msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "ctrl+c":
		m.code, m.queue = nil, nil
		return m, nil
	case "esc", "enter", "q":
		m.code = nil
		return m, m.drain()
	case "g", "home":
		m.code.view.GotoTop()
	case "G", "end":
		m.code.view.GotoBottom()
	default:
		var cmd tea.Cmd
		m.code.view, cmd = m.code.view.Update(msg)
		return m, cmd
	}
	return m, nil
}
