package main

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"

	"charm.land/bubbles/v2/textarea"
	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

var modes = []string{"plan", "edit", "auto"}

var spinnerFrames = []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}

type (
	eventMsg        struct{ ev voss.TypedEvent }
	streamClosedMsg struct{}
	tickMsg         struct{ gen int }
	liveMsg         struct{}
	errMsg          struct {
		what string
		err  error
	}
	// conflictMsg is a 409: another turn was running, so the text goes back in the queue.
	conflictMsg struct{ text string }
	costMsg     voss.CostInfo
)

type chatModel struct {
	ctx       context.Context
	client    *voss.Client
	sessionID string
	cwd       string
	events    <-chan voss.TypedEvent

	turn      turn
	mode      string
	editor    textarea.Model
	queue     []string
	sentAt    time.Time
	frame     int
	tickGen   int
	width     int
	height    int
	dark      bool
	r         renderer
	blocks    []block
	rendered  []string
	vp        viewport.Model
	follow    bool
	live      string
	liveTick  bool
	lastCtrlC time.Time
	quitting  bool
	offline   bool
}

func newChatModel(ctx context.Context, client *voss.Client, sessionID, cwd string, events <-chan voss.TypedEvent) chatModel {
	ed := textarea.New()
	ed.ShowLineNumbers = false
	ed.Placeholder = "message voss"
	ed.SetPromptFunc(2, func(info textarea.PromptInfo) string {
		if info.LineNumber == 0 {
			return "› "
		}
		return "  "
	})
	ed.DynamicHeight = true
	ed.MinHeight = 1
	ed.MaxHeight = 10
	ed.KeyMap.InsertNewline.SetKeys("shift+enter", "ctrl+j")
	ed.Focus()
	return chatModel{
		ctx:       ctx,
		client:    client,
		sessionID: sessionID,
		cwd:       cwd,
		events:    events,
		turn:      turn{model: "—"},
		mode:      modes[0],
		editor:    ed,
		dark:      true,
		r:         newRenderer(0, true),
		vp:        viewport.New(),
		follow:    true,
	}
}

func (m chatModel) Init() tea.Cmd {
	return tea.Batch(tea.RequestBackgroundColor, waitEvent(m.events))
}

func waitEvent(ch <-chan voss.TypedEvent) tea.Cmd {
	return func() tea.Msg {
		ev, ok := <-ch
		if !ok {
			return streamClosedMsg{}
		}
		return eventMsg{ev}
	}
}

// startTicking starts a spinner loop and retires any older one.
func (m *chatModel) startTicking() tea.Cmd {
	m.tickGen++
	return tick(m.tickGen)
}

func tick(gen int) tea.Cmd {
	return tea.Tick(100*time.Millisecond, func(time.Time) tea.Msg { return tickMsg{gen} })
}

func (m chatModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	next, cmd := m.update(msg)
	cm := next.(chatModel)
	cm.layout()
	return cm, cmd
}

func (m chatModel) update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width, m.height = msg.Width, msg.Height
		m.editor.SetWidth(msg.Width)
		m.rerender()
		return m, nil

	case tea.BackgroundColorMsg:
		m.dark = msg.IsDark()
		m.rerender()
		return m, nil

	case tea.MouseWheelMsg:
		var cmd tea.Cmd
		m.vp, cmd = m.vp.Update(msg)
		m.follow = m.vp.AtBottom()
		return m, cmd

	case liveMsg:
		m.liveTick = false
		m.live = m.renderLive()
		return m, nil

	case eventMsg:
		wasBusy, wasStreaming := m.turn.busy, m.turn.streaming
		var blocks []block
		m.turn, blocks = reduce(m.turn, msg.ev)
		if _, user := msg.ev.(voss.UserEvent); user {
			m.follow = true
		}
		m.add(blocks...)
		cmds := []tea.Cmd{waitEvent(m.events)}
		if m.turn.streaming == "" {
			m.live = ""
		} else if m.turn.streaming != wasStreaming && !m.liveTick {
			// Re-render streamed markdown at most 30 times a second.
			m.liveTick = true
			cmds = append(cmds, tea.Tick(time.Second/30, func(time.Time) tea.Msg { return liveMsg{} }))
		}
		if m.turn.busy && !wasBusy {
			m.sentAt = time.Now()
			cmds = append(cmds, m.startTicking())
		}
		if _, idle := msg.ev.(voss.SessionIdle); idle && len(m.queue) > 0 {
			text := m.queue[0]
			m.queue = m.queue[1:]
			cmds = append(cmds, m.send(text))
		}
		return m, tea.Batch(cmds...)

	case streamClosedMsg:
		m.turn.busy = false
		m.offline = true
		m.add(block{blockError, "lost the connection to voss serve (ctrl+d quits)"})
		return m, nil

	case tickMsg:
		if !m.turn.busy || msg.gen != m.tickGen {
			return m, nil
		}
		m.frame++
		return m, tick(m.tickGen)

	case conflictMsg:
		m.queue = append([]string{msg.text}, m.queue...)
		m.turn.busy = true
		return m, nil

	case errMsg:
		if msg.what == "send" {
			m.turn.busy = false
		}
		m.add(block{blockError, msg.what + ": " + errText(msg.err)})
		return m, nil

	case costMsg:
		m.add(block{blockNotice, fmt.Sprintf("cost: $%.4f over %d turn(s)", msg.TotalUsd, msg.Turns)})
		return m, nil

	case tea.KeyPressMsg:
		return m.handleKey(msg)
	}

	var cmd tea.Cmd
	m.editor, cmd = m.editor.Update(msg)
	return m, cmd
}

func (m chatModel) handleKey(msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	key := msg.String()

	if p := m.turn.permission; p != nil && key != "esc" && key != "ctrl+c" {
		choices := "aAd"
		if p.ToolName == "scope_expand" {
			choices = "yn"
		}
		if len(key) == 1 && strings.Contains(choices, key) {
			m.turn.permission = nil
			return m, m.replyPermission(p.Id, key)
		}
		return m, nil
	}

	switch key {
	case "ctrl+c":
		if time.Since(m.lastCtrlC) < time.Second {
			return m.quit()
		}
		m.lastCtrlC = time.Now()
		m.editor.Reset()
		return m, nil

	case "ctrl+d":
		if m.editor.Value() == "" {
			return m.quit()
		}

	case "esc":
		if !m.turn.busy {
			return m, nil
		}
		// Queued messages go back to the editor instead of sending after the abort.
		if len(m.queue) > 0 {
			restored := append(m.queue, m.editor.Value())
			m.queue = nil
			m.editor.SetValue(strings.TrimRight(strings.Join(restored, "\n"), "\n"))
		}
		m.turn.thinking = "aborting"
		return m, m.abort()

	case "ctrl+o":
		if m.turn.lastTool != nil {
			m.add(block{blockToolArgs, toolArgsText(*m.turn.lastTool)})
		}
		return m, nil

	case "pgup":
		m.vp.PageUp()
		m.follow = m.vp.AtBottom()
		return m, nil

	case "pgdown":
		m.vp.PageDown()
		m.follow = m.vp.AtBottom()
		return m, nil

	case "shift+tab":
		for i, mode := range modes {
			if mode == m.mode {
				m.mode = modes[(i+1)%len(modes)]
				break
			}
		}
		return m, nil

	case "enter":
		text := strings.TrimSpace(m.editor.Value())
		if text == "" {
			return m, nil
		}
		m.editor.Reset()
		if strings.HasPrefix(text, "/") {
			return m.slash(text)
		}
		if m.offline {
			m.editor.SetValue(text)
			m.add(block{blockError, "not connected to voss serve (ctrl+d quits)"})
			return m, nil
		}
		if m.turn.busy {
			m.queue = append(m.queue, text)
			return m, nil
		}
		cmd := m.send(text)
		return m, cmd
	}

	var cmd tea.Cmd
	m.editor, cmd = m.editor.Update(msg)
	return m, cmd
}

func (m chatModel) quit() (tea.Model, tea.Cmd) {
	m.quitting = true
	return m, tea.Quit
}

func (m chatModel) slash(text string) (tea.Model, tea.Cmd) {
	switch strings.Fields(text)[0] {
	case "/quit":
		return m.quit()
	case "/cost":
		client, ctx, id := m.client, m.ctx, m.sessionID
		return m, func() tea.Msg {
			c, err := client.Cost(ctx, id)
			if err != nil {
				return errMsg{"cost", err}
			}
			return costMsg(c)
		}
	case "/help":
		m.add(block{blockNotice, "commands: /help /cost /quit"})
		return m, nil
	}
	m.add(block{blockNotice, text + " is not available in this client"})
	return m, nil
}

// send posts a message with the current mode.
func (m *chatModel) send(text string) tea.Cmd {
	m.turn.busy = true
	m.turn.thinking = ""
	m.sentAt = time.Now()
	m.follow = true
	client, ctx, id, mode := m.client, m.ctx, m.sessionID, m.mode
	post := func() tea.Msg {
		err := client.PostMessage(ctx, id, text, mode)
		var ve *voss.VossError
		if errors.As(err, &ve) && ve.Status == http.StatusConflict {
			return conflictMsg{text}
		}
		if err != nil {
			return errMsg{"send", err}
		}
		return nil
	}
	return tea.Batch(post, m.startTicking())
}

func (m chatModel) abort() tea.Cmd {
	client, ctx, id := m.client, m.ctx, m.sessionID
	return func() tea.Msg {
		if err := client.Abort(ctx, id); err != nil {
			return errMsg{"abort", err}
		}
		return nil
	}
}

func (m chatModel) replyPermission(reqID, choice string) tea.Cmd {
	client, ctx, id := m.client, m.ctx, m.sessionID
	return func() tea.Msg {
		// A stale reply means the request was already answered or timed out.
		if _, err := client.PermissionReply(ctx, id, reqID, choice); err != nil {
			return errMsg{"permission", err}
		}
		return nil
	}
}

func (m chatModel) View() tea.View {
	if m.quitting {
		return tea.NewView("")
	}
	v := tea.NewView(m.vp.View() + "\n" + m.bottom())
	v.AltScreen = true
	v.MouseMode = tea.MouseModeCellMotion
	return v
}

// bottom is everything under the transcript: the prompt, the editor and the footer.
func (m chatModel) bottom() string {
	var parts []string
	if p := m.turn.permission; p != nil {
		parts = append(parts, m.r.permission(*p, m.cwd))
	}
	parts = append(parts, m.editor.View(), ansi.Truncate(m.footer(), m.r.width, "…"))
	return strings.Join(parts, "\n")
}

// layout sizes the transcript to the space the bottom area leaves and keeps
// it on the newest line while following.
func (m *chatModel) layout() {
	m.vp.SetWidth(m.r.width)
	m.vp.SetHeight(max(m.height-lipgloss.Height(m.bottom()), 1))
	content := strings.Join(m.rendered, "\n")
	if m.live != "" {
		if content != "" {
			content += "\n"
		}
		content += m.live
	}
	m.vp.SetContent(content)
	if m.follow {
		m.vp.GotoBottom()
	}
}

// add commits finished blocks to the transcript.
func (m *chatModel) add(blocks ...block) {
	for _, b := range blocks {
		m.blocks = append(m.blocks, b)
		m.rendered = append(m.rendered, m.r.block(b))
	}
}

// rerender rebuilds every block for a new width or background.
func (m *chatModel) rerender() {
	m.r = newRenderer(m.width, m.dark)
	for i, b := range m.blocks {
		m.rendered[i] = m.r.block(b)
	}
	m.live = m.renderLive()
}

func (m chatModel) footer() string {
	var left string
	if m.turn.busy {
		label := m.turn.thinking
		if label == "" {
			label = "working"
		}
		elapsed := int(time.Since(m.sentAt).Seconds())
		left = fmt.Sprintf("%s %s · %ds · esc to abort", spinnerFrames[m.frame%len(spinnerFrames)], label, elapsed)
		if n := len(m.queue); n > 0 {
			left += fmt.Sprintf(" · %d queued", n)
		}
		left += " · "
	}
	return styleDim.Render(left + fmt.Sprintf("%s mode · %s · %d tok · $%.4f · ctx %.0f%%",
		m.mode, m.turn.model, m.turn.tokens, m.turn.costUSD, m.turn.ctxPct*100))
}

func (m chatModel) renderLive() string {
	if m.turn.streaming == "" {
		return ""
	}
	return m.r.markdown(m.turn.streaming)
}
