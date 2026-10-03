package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	tea "charm.land/bubbletea/v2"
	voss "github.com/vosslang/voss/sdk/go"
)

type sessionConnection struct {
	meta   sessionMeta
	events <-chan voss.TypedEvent
	cancel context.CancelFunc
}

type sessionEventMsg struct {
	events <-chan voss.TypedEvent
	ev     voss.TypedEvent
}

type resumeMsg struct {
	conn sessionConnection
	err  error
}

type resumeListMsg struct {
	sessions []voss.SavedSession
	err      error
}

func openChatSession(ctx context.Context, client *voss.Client, o options) (sessionConnection, error) {
	s, err := client.OpenSession(ctx, voss.SessionOptions{Cwd: o.cwd, Model: o.model, Resume: o.resume})
	if err != nil {
		return sessionConnection{}, fmt.Errorf("open session: %w", err)
	}
	info, err := client.GetSession(ctx, s.Id)
	if err != nil {
		return sessionConnection{}, fmt.Errorf("read session: %w", err)
	}
	streamCtx, cancel := context.WithCancel(ctx)
	events, err := client.Events(streamCtx, s.Id)
	if err != nil {
		cancel()
		return sessionConnection{}, fmt.Errorf("event stream: %w", err)
	}
	return sessionConnection{
		meta: sessionMeta{
			ID: s.Id, Cwd: info.Cwd, Model: info.Model,
			Provider: providerLabel(s.Auth), Git: gitSummary(info.Cwd),
			Resume: resumeRow(info.Cwd, s.Id, time.Now()),
		},
		events: events, cancel: cancel,
	}, nil
}

func (m *chatModel) resumeSession(id string) tea.Cmd {
	if id == m.sessionID {
		m.add(roleBlock("system", "already in session: "+id))
		return nil
	}
	m.resuming = true
	client, ctx, cwd := m.client, m.ctx, m.cwd
	return func() tea.Msg {
		conn, err := openChatSession(ctx, client, options{cwd: cwd, resume: id})
		return resumeMsg{conn, err}
	}
}

func (m chatModel) resumeFailed(err error) (tea.Model, tea.Cmd) {
	m.add(roleBlock("error", "resume: "+errText(err)))
	if len(m.queue) > 0 {
		m.editor.SetValue(strings.Join(append(m.queue, m.editor.Value()), "\n"))
		m.queue = nil
	}
	return m, nil
}
