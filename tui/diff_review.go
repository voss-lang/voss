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

type diffReviewPanel struct {
	proposal   voss.DiffProposed
	decisions  []voss.DiffReplyDecisions
	view       viewport.Model
	offsets    []int
	submitting bool
	err        string
}

type diffReplyMsg struct {
	sessionID, id string
	stale         bool
	err           error
}

func (p *diffReviewPanel) resize(width, height int) {
	p.view.SetWidth(max(width-4, 1))
	p.view.SetHeight(max(height-5, 1))
	p.offsets = nil
	var rows []string
	for i, h := range p.proposal.Hunks {
		p.offsets = append(p.offsets, len(rows))
		mark := "pending"
		if i < len(p.decisions) {
			mark = string(p.decisions[i])
		} else if i == len(p.decisions) {
			mark = "reviewing"
		}
		name := strings.Join(strings.Fields(ansi.Strip(h.File)), " ")
		header := fmt.Sprintf("[%d/%d] %s:%d · %s", i+1, len(p.proposal.Hunks), name, h.Start, mark)
		rows = append(rows, lipgloss.NewStyle().Foreground(col(palette.Accent)).Render(ansi.Truncate(header, p.view.Width(), "…")))
		for _, line := range h.Lines {
			color := palette.OutputText
			if strings.HasPrefix(line, "+") {
				color = palette.Good
			} else if strings.HasPrefix(line, "-") {
				color = palette.Error
			}
			text := strings.ReplaceAll(ansi.Strip(line), "\t", "    ")
			wrapped := lipgloss.NewStyle().Foreground(col(color)).Render(ansi.Wrap(text, p.view.Width(), ""))
			rows = append(rows, strings.Split(wrapped, "\n")...)
		}
		rows = append(rows, "")
	}
	p.view.SetContent(strings.Join(rows, "\n"))
}

func (p diffReviewPanel) screen(width, height int) string {
	inner := max(width-4, 1)
	help := "y accept · n reject · s skip · a accept rest · q reject rest"
	status := "Reject/skip cancels batch · Esc cancel · ↑/↓ scroll · PgUp/PgDn page"
	if p.submitting {
		status = "Waiting for server… · Ctrl+C abort"
	} else if p.err != "" {
		help = "Enter retry · Esc cancel · Ctrl+C abort"
		status = p.err
	}
	screen := strings.Join([]string{
		"  " + lipgloss.NewStyle().Foreground(col(palette.Accent)).Render(ansi.Truncate("Review changes", inner, "…")),
		"", lipgloss.NewStyle().Padding(0, 2).Render(p.view.View()), "",
		"  " + styleDim.Render(ansi.Truncate(help, inner, "…")),
		"  " + styleDim.Render(ansi.Truncate(status, inner, "…")),
	}, "\n")
	return strings.Join(strings.Split(screen, "\n")[:min(lipgloss.Height(screen), height)], "\n")
}

func (m chatModel) reviewKey(msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	p := m.review
	key := msg.String()
	if key == "ctrl+c" {
		m.queue = nil
		m.turn.interrupted = true
		p.submitting = true
		return m, m.abort()
	}
	if p.submitting {
		return m, nil
	}
	switch key {
	case "esc":
		p.decisions = nil
		return m, m.replyDiff()
	case "enter":
		if p.err != "" {
			return m, m.replyDiff()
		}
	case "y", "n", "s", "a", "q":
		if len(p.decisions) == len(p.proposal.Hunks) {
			return m, nil
		}
		choice := map[string]voss.DiffReplyDecisions{"y": voss.Accept, "a": voss.Accept, "n": voss.Reject, "q": voss.Reject, "s": voss.Skip}[key]
		p.decisions = append(p.decisions, choice)
		if key == "a" || key == "q" {
			for len(p.decisions) < len(p.proposal.Hunks) {
				p.decisions = append(p.decisions, choice)
			}
		}
		if len(p.decisions) == len(p.proposal.Hunks) {
			return m, m.replyDiff()
		}
		p.resize(m.width, m.height)
		p.view.SetYOffset(p.offsets[len(p.decisions)])
	case "g", "home":
		p.view.GotoTop()
	case "G", "end":
		p.view.GotoBottom()
	default:
		var cmd tea.Cmd
		p.view, cmd = p.view.Update(msg)
		return m, cmd
	}
	return m, nil
}

func (m chatModel) replyDiff() tea.Cmd {
	p := m.review
	p.submitting, p.err = true, ""
	id := p.proposal.Id
	decisions := append([]voss.DiffReplyDecisions{}, p.decisions...)
	return func() tea.Msg {
		stale, err := m.client.ReplyDiff(m.ctx, m.sessionID, id, decisions)
		return diffReplyMsg{sessionID: m.sessionID, id: id, stale: stale, err: err}
	}
}
