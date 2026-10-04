package main

import (
	"fmt"
	"strconv"
	"strings"

	tea "charm.land/bubbletea/v2"
	voss "github.com/vosslang/voss/sdk/go"
)

type modelListMsg struct {
	id      string
	kind    paletteKind
	catalog voss.ModelCatalog
	err     error
}

type modelSelectedMsg struct {
	id   string
	info voss.SessionInfo
	err  error
}

func (m *chatModel) modelCommand(name string, args []string) tea.Cmd {
	if name == "/auth" && len(args) > 1 {
		m.add(output("", "usage: /auth [claude|codex|api]")...)
		return nil
	}
	if len(args) > 0 {
		selection := voss.ModelSelection{Model: strings.Join(args, " ")}
		if name == "/auth" {
			selection = voss.ModelSelection{Auth: args[0]}
		}
		return m.selectModel(selection)
	}
	m.selecting = true
	client, ctx, id := m.client, m.ctx, m.sessionID
	kind := paletteModel
	if name == "/auth" {
		kind = paletteAuth
	}
	return func() tea.Msg {
		catalog, err := client.ListModels(ctx)
		return modelListMsg{id, kind, catalog, err}
	}
}

func (m *chatModel) selectModel(selection voss.ModelSelection) tea.Cmd {
	m.selecting = true
	client, ctx, id := m.client, m.ctx, m.sessionID
	return func() tea.Msg {
		info, err := client.SelectModel(ctx, id, selection)
		return modelSelectedMsg{id, info, err}
	}
}

func (m *chatModel) restoreQueuedInput() {
	if len(m.queue) > 0 {
		m.editor.SetValue(strings.TrimSpace(strings.Join(append(m.queue, m.editor.Value()), "\n")))
		m.queue = nil
	}
}

func (m *chatModel) syncModelPalette(kind paletteKind, query string) {
	m.pal = picker{kind: kind}
	query = strings.ToLower(strings.TrimSpace(query))
	if kind == paletteAuth {
		for _, mode := range []string{"claude", "codex", "api"} {
			connected := false
			for _, choice := range m.modelChoices {
				connected = connected || (string(choice.Auth) == mode && choice.Connected)
			}
			label := mode + "  ·  " + connectionLabel(connected)
			if mode != "api" {
				label += "  ·  local subscription"
			}
			if m.authMode() == mode {
				label = "● " + label
			}
			if strings.Contains(label, query) {
				m.pal.names = append(m.pal.names, mode)
				m.pal.labels = append(m.pal.labels, label)
			}
		}
		return
	}
	for i, choice := range m.modelChoices {
		if !strings.Contains(strings.ToLower(choice.Id+" "+choice.Name+" "+choice.ProviderLabel), query) {
			continue
		}
		label := choice.Name + "  ·  " + choice.ProviderLabel + "  ·  " + connectionLabel(choice.Connected)
		if choice.Recommended {
			label += "  ·  recommended"
		}
		if (m.turn.model == choice.Id || m.turn.model == "openai/"+choice.Id) && m.authMode() == string(choice.Auth) &&
			(choice.Auth != "api" || m.provider == strings.TrimSuffix(choice.ProviderLabel, " API")) {
			label = "● " + label
		}
		m.pal.names = append(m.pal.names, strconv.Itoa(i))
		m.pal.labels = append(m.pal.labels, label)
	}
}

func connectionLabel(connected bool) string {
	if connected {
		return "connected"
	}
	return "login required"
}

func (m chatModel) authMode() string {
	switch m.auth {
	case "claude-agent":
		return "claude"
	case "codex-oauth":
		return "codex"
	default:
		return "api"
	}
}

func (m chatModel) chooseModel() (tea.Model, tea.Cmd) {
	name := m.pal.names[m.pal.idx]
	selection := voss.ModelSelection{Auth: name}
	if m.pal.kind == paletteModel {
		i, _ := strconv.Atoi(name)
		choice := m.modelChoices[i]
		selection = voss.ModelSelection{Model: choice.Id, Auth: string(choice.Auth), Provider: choice.Provider}
	}
	m.pal = picker{}
	m.editor.Reset()
	return m, m.selectModel(selection)
}

func (m chatModel) modelSelected(msg modelSelectedMsg) (tea.Model, tea.Cmd) {
	if msg.id != m.sessionID {
		return m, nil
	}
	m.selecting = false
	if msg.err != nil {
		m.add(output("", "model switch: "+errText(msg.err))...)
		m.restoreQueuedInput()
		return m, nil
	}
	m.turn.model, m.provider, m.auth = msg.info.Model, msg.info.Provider, msg.info.Auth
	for i := range m.home {
		if m.home[i][0] == "model" {
			m.home[i][1] = m.provider + " / " + m.turn.model
		}
	}
	m.add(output(fmt.Sprintf("model: %s / %s\nauth: %s (persisted)", m.provider, m.turn.model, m.auth), "")...)
	return m, m.drain()
}
