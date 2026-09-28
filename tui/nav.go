package main

import (
	"fmt"
	"regexp"
	"strings"
	"time"

	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
)

// Transcript nav mode, copying and trimming, from turn_view.py and app.py.

const (
	trimThreshold = 500
	trimKeep      = 400
	toastDismiss  = 1500 * time.Millisecond
)

type toastExpiredMsg struct{ gen int }

// showToast shows a timed toast, which replaces the thinking toast for 1.5 s.
func (m *chatModel) showToast(text string) tea.Cmd {
	m.toastGen++
	m.toast = text
	gen := m.toastGen
	return tea.Tick(toastDismiss, func(time.Time) tea.Msg { return toastExpiredMsg{gen} })
}

var fenceRE = regexp.MustCompile("(?s)```[^\n]*\n(.*?)```")

// extractLastCodeBlock returns the body of the last fenced block, like
// app.extract_last_code_block.
func extractLastCodeBlock(text string) (string, bool) {
	blocks := fenceRE.FindAllStringSubmatch(text, -1)
	if len(blocks) == 0 {
		return "", false
	}
	return strings.TrimRight(blocks[len(blocks)-1][1], "\n"), true
}

// copyCode is Ctrl+Y: the last code block of the latest answer, or the
// whole answer.
func (m *chatModel) copyCode() tea.Cmd {
	code, isBlock := extractLastCodeBlock(m.lastResponse)
	payload := code
	if !isBlock {
		payload = strings.TrimSpace(m.lastResponse)
	}
	if payload == "" {
		return m.showToast("nothing to copy yet")
	}
	msg := "copied response"
	if isBlock {
		msg = "copied code block"
	}
	return tea.Batch(tea.SetClipboard(payload), m.showToast(msg))
}

// plainText is what nav-mode y copies for a block, like each widget's plain_text.
func (b block) plainText() string {
	switch b.kind {
	case blockRole:
		return b.role + "\n" + b.text
	case blockAssistant:
		return strings.Join(nonEmpty(b.text, b.footer), "\n")
	case blockShell:
		return strings.Join(nonEmpty("! "+b.text, b.body, fmt.Sprintf("· exit %d", b.exit)), "\n")
	case blockNote:
		return "# note saved"
	case blockConfidence:
		return fmt.Sprintf("%.2f", b.conf)
	}
	return b.text
}

func (m *chatModel) navKey(key string) tea.Cmd {
	pendingG := m.pendingG
	m.pendingG = false
	switch key {
	case "j", "down":
		m.navSet(m.navIdx + 1)
	case "k", "up":
		m.navSet(m.navIdx - 1)
	case "y":
		if m.navIdx < 0 || m.navIdx >= len(m.blocks) {
			return nil
		}
		text := m.blocks[m.navIdx].plainText()
		if text == "" {
			return m.showToast("nothing to copy")
		}
		return tea.Batch(tea.SetClipboard(text), m.showToast("copied block"))
	case "g":
		if pendingG {
			m.navSet(0)
			m.vp.GotoTop()
		} else {
			m.pendingG = true
		}
	case "G":
		m.navSet(len(m.blocks) - 1)
		m.follow = true
	}
	return nil
}

// navSet focuses block i, clamped, and scrolls it into view.
func (m *chatModel) navSet(i int) {
	if len(m.blocks) == 0 {
		m.navIdx = -1
		return
	}
	m.navIdx = max(0, min(len(m.blocks)-1, i))
	top := m.trimLines()
	for _, r := range m.rendered[:m.navIdx] {
		top += lipgloss.Height(r)
	}
	height := lipgloss.Height(m.rendered[m.navIdx])
	if top < m.vp.YOffset() || top+height > m.vp.YOffset()+m.vp.Height() {
		m.vp.SetYOffset(top)
		m.follow = false
	}
}

// trim flattens the oldest blocks into a placeholder above 500 blocks,
// keeping the newest 400, as TranscriptView._trim does.
func (m *chatModel) trim() {
	if len(m.blocks) <= trimThreshold {
		return
	}
	drop := len(m.blocks) - trimKeep
	m.trimmed += drop
	m.blocks = append([]block(nil), m.blocks[drop:]...)
	m.rendered = append([]string(nil), m.rendered[drop:]...)
	if m.navIdx >= 0 {
		m.navIdx = max(m.navIdx-drop, 0)
	}
}

func (m chatModel) trimLines() int {
	if m.trimmed == 0 {
		return 0
	}
	return 1
}

func (m chatModel) trimPlaceholder() string {
	return lipgloss.NewStyle().Faint(true).Render(fmt.Sprintf("%s %d earlier turns · /resume to reload", glyphs.Approx, m.trimmed))
}

// tint gives a rendered block Textual's .nav-focus background, re-applying
// it after every reset so styled spans keep it, and fills the width.
func tint(block string, width int) string {
	bg := lipgloss.NewStyle().Background(blend(palette.Accent, palette.Bg, 0.08)).Render(" ")
	seq := bg[:strings.Index(bg, " ")]
	lines := strings.Split(block, "\n")
	for i, l := range lines {
		l = strings.NewReplacer("\x1b[0m", "\x1b[0m"+seq, "\x1b[m", "\x1b[m"+seq, "\x1b[49m", "\x1b[49m"+seq).Replace(l)
		lines[i] = seq + l + strings.Repeat(" ", max(width-lipgloss.Width(l), 0)) + "\x1b[0m"
	}
	return strings.Join(lines, "\n")
}
