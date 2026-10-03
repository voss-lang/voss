package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"

	tea "charm.land/bubbletea/v2"
)

type killRing struct {
	items             []string
	lastKey           string
	index, start, end int
}

func (m *chatModel) killText(msg tea.KeyPressMsg, join bool) tea.Cmd {
	before := []rune(m.editor.Value())
	var cmd tea.Cmd
	m.editor, cmd = m.editor.Update(msg)
	n := len(before) - len([]rune(m.editor.Value()))
	if n == 0 {
		return cmd
	}
	start := m.cursorOffset()
	killed := m.expandPastes(string(before[start : start+n]))
	if join {
		i := len(m.kills.items) - 1
		if msg.String() == "ctrl+u" || msg.String() == "ctrl+w" {
			m.kills.items[i] = killed + m.kills.items[i]
		} else {
			m.kills.items[i] += killed
		}
	} else {
		m.kills.items = append(m.kills.items, killed)
	}
	m.kills.lastKey = msg.String()
	return cmd
}

func (m *chatModel) yankKill(cycle bool) {
	k := &m.kills
	if len(k.items) == 0 {
		return
	}
	if cycle {
		value := []rune(m.editor.Value())
		m.editor.SetValue(string(value[:k.start]) + string(value[k.end:]))
		m.moveCursorTo(k.start)
		k.index = (k.index + len(k.items) - 1) % len(k.items)
	} else {
		m.editor.DeleteSelection()
		k.start = m.cursorOffset()
		k.index = len(k.items) - 1
	}
	m.editor.InsertString(k.items[k.index])
	k.end = m.cursorOffset()
	k.lastKey = "alt+y"
}

type editorDoneMsg struct {
	text string
	err  error
}

func promptEditor(ctx context.Context, cwd, text string) (*exec.Cmd, tea.ExecCallback, error) {
	editor := os.Getenv("EDITOR")
	if editor == "" {
		editor = "vi"
	}
	argv, err := shlexSplit(editor)
	if err != nil {
		return nil, nil, err
	}
	if len(argv) == 0 {
		return nil, nil, fmt.Errorf("EDITOR is empty")
	}
	f, err := os.CreateTemp("", "voss-prompt-*.md")
	if err != nil {
		return nil, nil, err
	}
	_, writeErr := f.WriteString(text)
	closeErr := f.Close()
	if writeErr != nil || closeErr != nil {
		os.Remove(f.Name())
		if writeErr != nil {
			return nil, nil, writeErr
		}
		return nil, nil, closeErr
	}
	c := exec.CommandContext(ctx, argv[0], append(argv[1:], f.Name())...)
	c.Dir = cwd
	done := func(err error) tea.Msg {
		defer os.Remove(f.Name())
		if err != nil {
			return editorDoneMsg{err: err}
		}
		data, err := os.ReadFile(f.Name())
		return editorDoneMsg{text: string(data), err: err}
	}
	return c, done, nil
}
