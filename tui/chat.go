package main

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"sort"
	"strings"
	"time"

	"charm.land/bubbles/v2/textarea"
	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	voss "github.com/vosslang/voss/sdk/go"
)

var modes = []string{"plan", "edit", "auto"}

var spinnerFrames = []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}

var (
	styleUser    = lipgloss.NewStyle().Bold(true)
	styleDim     = lipgloss.NewStyle().Faint(true)
	styleTool    = lipgloss.NewStyle().Foreground(lipgloss.Yellow)
	styleClarify = lipgloss.NewStyle().Foreground(lipgloss.Cyan)
	styleError   = lipgloss.NewStyle().Foreground(lipgloss.Red)
)

type (
	eventMsg        struct{ ev voss.TypedEvent }
	streamClosedMsg struct{}
	tickMsg         struct{ gen int }
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
	events    <-chan voss.TypedEvent

	turn      turn
	mode      string
	editor    textarea.Model
	queue     []string
	sentAt    time.Time
	frame     int
	tickGen   int
	width     int
	lastCtrlC time.Time
	quitting  bool
	offline   bool
}

func newChatModel(ctx context.Context, client *voss.Client, sessionID string, events <-chan voss.TypedEvent) chatModel {
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
		events:    events,
		turn:      turn{model: "—"},
		mode:      modes[0],
		editor:    ed,
	}
}

func (m chatModel) Init() tea.Cmd {
	return tea.Batch(
		tea.Println(styleDim.Render("voss · session "+short(m.sessionID, 8)+" · enter sends · shift+tab mode · esc aborts · ctrl+d quits")),
		waitEvent(m.events),
	)
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
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.editor.SetWidth(msg.Width)
		return m, nil

	case eventMsg:
		wasBusy := m.turn.busy
		var blocks []block
		m.turn, blocks = reduce(m.turn, msg.ev)
		// Print before reading the next event so scrollback keeps event order.
		cmds := []tea.Cmd{tea.Sequence(printBlocks(blocks), waitEvent(m.events))}
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
		return m, printBlocks([]block{{blockError, "lost the connection to voss serve (ctrl+d quits)"}})

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
		return m, printBlocks([]block{{blockError, msg.what + ": " + errText(msg.err)}})

	case costMsg:
		return m, printBlocks([]block{{blockNotice, fmt.Sprintf("cost: $%.4f over %d turn(s)", msg.TotalUsd, msg.Turns)}})

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
			return m, printBlocks([]block{{blockError, "not connected to voss serve (ctrl+d quits)"}})
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

// quit clears the live region so the editor is not left in scrollback.
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
		return m, printBlocks([]block{{blockNotice, "commands: /help /cost /quit"}})
	}
	return m, printBlocks([]block{{blockNotice, text + " is not available in this client"}})
}

// send posts a message with the current mode.
func (m *chatModel) send(text string) tea.Cmd {
	m.turn.busy = true
	m.turn.thinking = ""
	m.sentAt = time.Now()
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
	var parts []string
	if m.turn.streaming != "" {
		parts = append(parts, m.wrap(m.turn.streaming))
	}
	if p := m.turn.permission; p != nil {
		parts = append(parts, m.wrap(permissionPrompt(*p)))
	}
	parts = append(parts, m.editor.View(), m.footer())
	return tea.NewView(strings.Join(parts, "\n"))
}

func (m chatModel) wrap(s string) string {
	if m.width <= 0 {
		return s
	}
	return lipgloss.NewStyle().Width(m.width).Render(s)
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

func permissionPrompt(p voss.PermissionUpdated) string {
	if p.ToolName == "scope_expand" {
		target := ""
		if p.Args != nil {
			target = fmt.Sprint((*p.Args)["target"])
		}
		return styleTool.Render("⚠ expand scope to "+target+"?") + "  [y] yes  [n] no"
	}
	return styleTool.Render("⚠ allow "+p.ToolName+"?") + " " + styleDim.Render(argSummary(p.Args)) +
		"\n  [a] allow once  [A] always  [d] deny"
}

func argSummary(args *map[string]interface{}) string {
	if args == nil {
		return ""
	}
	keys := make([]string, 0, len(*args))
	for k := range *args {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	pairs := make([]string, len(keys))
	for i, k := range keys {
		pairs[i] = k + "=" + short(strings.ReplaceAll(fmt.Sprint((*args)[k]), "\n", "⏎"), 60)
	}
	return strings.Join(pairs, " ")
}

func printBlocks(blocks []block) tea.Cmd {
	if len(blocks) == 0 {
		return nil
	}
	lines := make([]string, len(blocks))
	for i, b := range blocks {
		lines[i] = renderBlock(b)
	}
	return tea.Println(strings.Join(lines, "\n"))
}

func renderBlock(b block) string {
	switch b.kind {
	case blockUser:
		return "\n" + styleUser.Render("› "+strings.ReplaceAll(b.text, "\n", "\n  "))
	case blockPlan, blockNotice:
		return styleDim.Render(b.text)
	case blockTool:
		return styleTool.Render("⚙ " + b.text)
	case blockClarify:
		return styleClarify.Render("? " + b.text)
	case blockWarning:
		return styleTool.Render("⚠ " + b.text)
	case blockError:
		return styleError.Render("✗ " + b.text)
	}
	return b.text
}

func errText(err error) string {
	var ve *voss.VossError
	if errors.As(err, &ve) && ve.Detail != "" {
		return ve.Detail
	}
	return err.Error()
}

func short(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n-1]) + "…"
}
