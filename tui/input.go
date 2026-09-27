package main

import (
	"fmt"
	"strings"

	tea "charm.land/bubbletea/v2"
)

// Input bar behaviours from voss/harness/tui/widgets/input_bar.py.

// pasteChipLines: a paste with more lines than this collapses to a chip.
const pasteChipLines = 5

// storePaste keeps a large paste and returns the chip token that stands in
// for it until submit.
func (m *chatModel) storePaste(text string) string {
	if m.pastes == nil {
		m.pastes = map[string]string{}
	}
	n := len(strings.Split(text, "\n"))
	token := fmt.Sprintf("[pasted %d lines]", n)
	for seq := 2; m.pastes[token] != ""; seq++ {
		token = fmt.Sprintf("[pasted %d lines #%d]", n, seq)
	}
	m.pastes[token] = text
	return token
}

// expandPastes swaps chip tokens back to their text when a line is submitted.
func (m *chatModel) expandPastes(value string) string {
	for token, blob := range m.pastes {
		value = strings.ReplaceAll(value, token, blob)
	}
	m.pastes = nil
	return value
}

// deleteChipBeforeCursor removes a whole chip token that ends at the cursor.
func (m *chatModel) deleteChipBeforeCursor() bool {
	value := []rune(m.editor.Value())
	lines := strings.Split(string(value), "\n")
	offset := m.editor.Line() + m.editor.Column()
	for _, l := range lines[:m.editor.Line()] {
		offset += len([]rune(l))
	}
	prefix := string(value[:min(offset, len(value))])
	for token := range m.pastes {
		if !strings.HasSuffix(prefix, token) {
			continue
		}
		cut := offset - len([]rune(token))
		m.editor.SetValue(string(value[:cut]) + string(value[offset:]))
		delete(m.pastes, token)
		m.moveCursorTo(cut)
		return true
	}
	return false
}

func (m *chatModel) moveCursorTo(offset int) {
	before := string([]rune(m.editor.Value())[:offset])
	line := strings.Count(before, "\n")
	m.editor.MoveToBegin()
	for range line {
		m.editor.CursorDown()
	}
	m.editor.SetCursorColumn(len([]rune(before[strings.LastIndex(before, "\n")+1:])))
}

// reverseSearch is Textual's Ctrl+R: the input shows the query and the match
// until Enter takes the match or Esc restores what was typed before.
type reverseSearch struct {
	active  bool
	query   string
	saved   string
	matches []string
	idx     int
}

// searchCorpus is the session's user messages, newest first, without repeats.
func (m chatModel) searchCorpus() []string {
	var out []string
	seen := map[string]bool{}
	for i := len(m.sent) - 1; i >= 0; i-- {
		if s := m.sent[i]; s != "" && !seen[s] {
			seen[s] = true
			out = append(out, s)
		}
	}
	return out
}

func (m *chatModel) refreshSearch() {
	q := strings.ToLower(m.search.query)
	m.search.matches = nil
	for _, item := range m.searchCorpus() {
		if strings.Contains(strings.ToLower(item), q) {
			m.search.matches = append(m.search.matches, item)
		}
	}
	m.search.idx = 0
}

func (m chatModel) searchLine() string {
	match := "(no match)"
	if m.search.idx < len(m.search.matches) {
		match = m.search.matches[m.search.idx]
	}
	return fmt.Sprintf("%s (reverse-i-search)`%s': %s", glyphs.Prompt, m.search.query, match)
}

func (m chatModel) searchKey(msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	switch key := msg.String(); {
	case key == "ctrl+r":
		if m.search.idx < len(m.search.matches)-1 {
			m.search.idx++
		} else {
			m.search.idx = len(m.search.matches)
		}
	case key == "enter":
		match := ""
		if m.search.idx < len(m.search.matches) {
			match = m.search.matches[m.search.idx]
		}
		m.search = reverseSearch{}
		m.editor.SetValue(match)
	case key == "esc":
		m.editor.SetValue(m.search.saved)
		m.search = reverseSearch{}
	case key == "backspace" || key == "ctrl+h":
		if r := []rune(m.search.query); len(r) > 0 {
			m.search.query = string(r[:len(r)-1])
		}
		m.refreshSearch()
	case msg.Text != "":
		m.search.query += msg.Text
		m.refreshSearch()
	}
	return m, nil
}
