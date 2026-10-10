package main

import (
	"strings"

	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

type inspectionPanel struct {
	result voss.InspectionResult
	view   viewport.Model
}

func (m *chatModel) showInspection(result voss.InspectionResult) {
	m.inspection = &inspectionPanel{result: result, view: viewport.New()}
	m.inspection.resize(m.width, m.height)
}

func (p *inspectionPanel) resize(width, height int) {
	p.view.SetWidth(max(width-4, 1))
	p.view.SetHeight(max(height-4, 1))
	text := strings.ReplaceAll(ansi.Strip(p.result.Text), "\t", "    ")
	p.view.SetContent(lipgloss.NewStyle().Foreground(col(palette.OutputText)).Render(ansi.Wrap(text, p.view.Width(), "")))
}

func (p inspectionPanel) screen(width, height int) string {
	inner := max(width-4, 1)
	title := strings.Join(strings.Fields(ansi.Strip(p.result.Title)), " ")
	screen := strings.Join([]string{
		"  " + lipgloss.NewStyle().Foreground(col(palette.Accent)).Render(ansi.Truncate(title, inner, "…")),
		"", lipgloss.NewStyle().Padding(0, 2).Render(p.view.View()), "",
		"  " + styleDim.Render(ansi.Truncate("↑/↓ scroll · PgUp/PgDn page · Esc/Enter close", inner, "…")),
	}, "\n")
	return strings.Join(strings.Split(screen, "\n")[:min(lipgloss.Height(screen), height)], "\n")
}

func (m chatModel) inspectionKey(msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "ctrl+c":
		m.inspection, m.queue = nil, nil
		return m, nil
	case "esc", "enter", "q":
		m.inspection = nil
		return m, m.drain()
	case "g", "home":
		m.inspection.view.GotoTop()
	case "G", "end":
		m.inspection.view.GotoBottom()
	default:
		var cmd tea.Cmd
		m.inspection.view, cmd = m.inspection.view.Update(msg)
		return m, cmd
	}
	return m, nil
}
