package main

import (
	"context"
	"errors"
	"net/http"
	"path/filepath"
	"slices"
	"strings"
	"time"

	"charm.land/bubbles/v2/textarea"
	"charm.land/bubbles/v2/viewport"
	tea "charm.land/bubbletea/v2"
	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

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
)

type chatModel struct {
	ctx       context.Context
	client    *voss.Client
	sessionID string
	cwd       string
	provider  string
	git       string
	home      [][2]string
	events    <-chan voss.TypedEvent

	turn     turn
	mode     string
	editor   textarea.Model
	queue    []string
	sentAt   time.Time
	frame    int
	tickGen  int
	width    int
	height   int
	r        renderer
	blocks   []block
	rendered []string
	vp       viewport.Model
	follow   bool
	live     string
	liveTick bool
	navMode  bool
	navIdx   int
	// detailExpanded is Ctrl+O's expand-all state; new cards open to match it.
	detailExpanded bool
	pendingG       bool
	trimmed        int
	toast          string
	toastGen       int
	// lastResponse is the latest answer, for Ctrl+Y.
	lastResponse string
	lastText     string
	pal          picker
	// paletteDismissed keeps a palette closed after Esc until the text changes.
	paletteDismissed bool
	mentionFiles     []string
	recentCommands   []string
	pastes           map[string]string
	search           reverseSearch
	sent             []string
	quitting         bool
	offline          bool
}

func newChatModel(ctx context.Context, client *voss.Client, meta sessionMeta, events <-chan voss.TypedEvent) chatModel {
	ed := textarea.New()
	ed.ShowLineNumbers = false
	ed.Prompt = ""
	ed.Placeholder = "/ commands · @ files · ctrl+r history"
	ed.DynamicHeight = true
	ed.MinHeight = 1
	ed.MaxHeight = 6
	ed.KeyMap.InsertNewline.SetKeys("shift+enter", "ctrl+j")
	surface := lipgloss.NewStyle().Background(col(palette.Surface))
	state := textarea.StyleState{
		Base:        surface,
		Text:        surface.Foreground(col(palette.Text)),
		CursorLine:  surface.Foreground(col(palette.Text)),
		Placeholder: surface.Foreground(col(palette.Dim)),
		EndOfBuffer: surface,
	}
	ed.SetStyles(textarea.Styles{Focused: state, Blurred: state, Cursor: textarea.CursorStyle{Color: col(palette.Accent)}})
	ed.Focus()
	return chatModel{
		ctx:       ctx,
		client:    client,
		sessionID: meta.ID,
		cwd:       meta.Cwd,
		provider:  meta.Provider,
		git:       meta.Git,
		home:      homeRows(meta),
		events:    events,
		turn:      turn{model: meta.Model},
		mode:      "plan",
		editor:    ed,
		r:         newRenderer(0),
		vp:        viewport.New(),
		follow:    true,
		navIdx:    -1,
	}
}

func (m chatModel) Init() tea.Cmd {
	return waitEvent(m.events)
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

// startTicking starts the working indicator's loop and retires any older one.
func (m *chatModel) startTicking() tea.Cmd {
	m.tickGen++
	m.frame = -1
	return tick(m.tickGen)
}

func tick(gen int) tea.Cmd {
	return tea.Tick(500*time.Millisecond, func(time.Time) tea.Msg { return tickMsg{gen} })
}

func (m chatModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	next, cmd := m.update(msg)
	cm := next.(chatModel)
	if v := cm.editor.Value(); v != cm.lastText || cm.search.active {
		cm.lastText = v
		cm.paletteDismissed = false
		cm.syncPalette()
	}
	cm.layout()
	return cm, cmd
}

func (m chatModel) update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width, m.height = msg.Width, msg.Height
		m.editor.SetWidth(max(msg.Width-8, 1))
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
		switch e := msg.ev.(type) {
		case voss.FinalEvent:
			m.lastResponse = e.Text
		case voss.StreamFinalize:
			m.lastResponse = m.turn.streaming
		}
		var blocks []block
		m.turn, blocks = reduce(m.turn, msg.ev)
		if u, user := msg.ev.(voss.UserEvent); user {
			m.follow = true
			m.sent = append(m.sent, u.Task)
		}
		m.add(blocks...)
		if e, ok := msg.ev.(voss.ToolEvent); ok {
			m.toolEvent(e)
		}
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
		if _, idle := msg.ev.(voss.SessionIdle); idle {
			cmds = append(cmds, m.drain())
		}
		return m, tea.Batch(cmds...)

	case streamClosedMsg:
		m.turn.busy = false
		m.offline = true
		m.add(roleBlock("error", "lost the connection to voss serve (ctrl+c quits)"))
		return m, nil

	case tickMsg:
		if !m.turn.busy || msg.gen != m.tickGen {
			return m, nil
		}
		m.frame++
		m.refreshRunningCards()
		return m, tick(m.tickGen)

	case conflictMsg:
		m.queue = append([]string{msg.text}, m.queue...)
		m.turn.busy = true
		return m, nil

	case errMsg:
		if msg.what == "send" {
			m.turn.busy = false
		}
		m.add(roleBlock("error", msg.what+": "+errText(msg.err)))
		return m, nil

	case shellDoneMsg:
		body := strings.Join(nonEmpty(strings.TrimRight(msg.stdout, " \t\n"), strings.TrimRight(msg.stderr, " \t\n")), "\n")
		m.add(block{kind: blockShell, text: msg.cmd, body: body, exit: msg.exit, joined: true})
		return m, nil

	case toastExpiredMsg:
		if msg.gen == m.toastGen {
			m.toast = ""
		}
		return m, nil

	case slashOutputMsg:
		m.add(output(msg.stdout, msg.stderr)...)
		return m, nil

	case tea.KeyPressMsg:
		return m.handleKey(msg)

	case tea.PasteMsg:
		if m.search.active || m.navMode {
			return m, nil
		}
		if len(strings.Split(msg.Content, "\n")) > pasteChipLines {
			m.editor.InsertString(m.storePaste(msg.Content))
			return m, nil
		}
	}

	var cmd tea.Cmd
	m.editor, cmd = m.editor.Update(msg)
	return m, cmd
}

func (m chatModel) handleKey(msg tea.KeyPressMsg) (tea.Model, tea.Cmd) {
	key := msg.String()

	if p := m.turn.permission; p != nil && key != "ctrl+c" {
		choices := map[string]string{"a": "a", "A": "A", "d": "d", "esc": "d"}
		if p.ToolName == "scope_expand" {
			// The server's scope check accepts y/once and always; anything else denies.
			choices = map[string]string{"y": "y", "a": "always", "n": "n", "esc": "n"}
		}
		if choice, ok := choices[key]; ok {
			m.turn.permission = nil
			return m, m.replyPermission(p.Id, choice)
		}
		return m, nil
	}

	if m.search.active {
		return m.searchKey(msg)
	}

	if m.pal.kind != paletteNone {
		switch key {
		case "up":
			m.pal.idx = max(m.pal.idx-1, 0)
			return m, nil
		case "down":
			m.pal.idx = min(m.pal.idx+1, max(len(m.pal.names)-1, 0))
			return m, nil
		case "esc":
			m.pal, m.paletteDismissed = picker{}, true
			return m, nil
		case "enter":
			if len(m.pal.names) > 0 {
				return m.choosePalette()
			}
			m.pal = picker{}
		}
	}

	if key == "ctrl+y" {
		return m, m.copyCode()
	}

	if m.navMode {
		switch {
		case slices.Contains([]string{"ctrl+c", "tab", "shift+tab", "esc", "ctrl+l", "ctrl+o", "pgup", "pgdown"}, key):
		case slices.Contains([]string{"j", "k", "up", "down", "y", "g", "G", "enter"}, key):
			return m, m.navKey(key)
		case key == "i":
			m.setNav(false)
			return m, nil
		case msg.Text != "":
			m.setNav(false)
		default:
			return m, nil
		}
	}

	switch key {
	case "ctrl+c":
		// Textual clears the queue before aborting so nothing queued sends after.
		m.queue = nil
		if !m.turn.busy {
			return m.quit()
		}
		m.turn.interrupted = true
		return m, m.abort()

	case "tab", "shift+tab":
		m.setNav(!m.navMode)
		return m, nil

	case "esc":
		if !m.turn.busy {
			m.setNav(!m.navMode)
		}
		return m, nil

	case "ctrl+l":
		return m, tea.ClearScreen

	case "ctrl+r":
		m.search = reverseSearch{active: true, saved: m.editor.Value()}
		m.refreshSearch()
		return m, nil

	case "backspace":
		if len(m.pastes) > 0 && m.deleteChipBeforeCursor() {
			return m, nil
		}

	case "ctrl+o":
		m.toggleAllCards()
		return m, nil

	case "pgup":
		m.vp.PageUp()
		m.follow = m.vp.AtBottom()
		return m, nil

	case "pgdown":
		m.vp.PageDown()
		m.follow = m.vp.AtBottom()
		return m, nil

	case "enter":
		text := strings.TrimSpace(m.expandPastes(m.editor.Value()))
		if text == "" {
			return m, nil
		}
		m.editor.Reset()
		// Like Textual's input bar, ! and # lines run at once, even mid-turn.
		if cmd, ok := strings.CutPrefix(text, "!"); ok {
			if cmd = strings.TrimSpace(cmd); cmd != "" {
				return m, runShell(m.ctx, m.cwd, cmd)
			}
			return m, nil
		}
		if note, ok := strings.CutPrefix(text, "#"); ok {
			if note = strings.TrimSpace(note); note != "" {
				if err := appendVossNote(filepath.Join(m.cwd, "VOSS.md"), note, time.Now()); err != nil {
					m.add(roleBlock("error", "note: "+err.Error()))
				} else {
					m.add(block{kind: blockNote, joined: true})
				}
			}
			return m, nil
		}
		if m.turn.busy {
			m.queue = append(m.queue, text)
			return m, nil
		}
		cmd := m.dispatch(text)
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

// dispatch runs one input line: a slash command locally, anything else as a
// turn. Live submits and queued lines both come through here, as in Textual.
func (m *chatModel) dispatch(text string) tea.Cmd {
	if strings.HasPrefix(text, "/") {
		return m.slash(text)
	}
	if m.offline {
		m.editor.SetValue(text)
		m.add(roleBlock("error", "not connected to voss serve (ctrl+c quits)"))
		return nil
	}
	return m.send(text)
}

// drain dispatches queued lines after a turn ends, running slash commands in
// order until a line starts the next turn.
func (m *chatModel) drain() tea.Cmd {
	var cmds []tea.Cmd
	for len(m.queue) > 0 && !m.turn.busy && !m.quitting {
		text := m.queue[0]
		m.queue = m.queue[1:]
		cmds = append(cmds, m.dispatch(text))
	}
	return tea.Batch(cmds...)
}

// send posts a message with the current mode.
func (m *chatModel) send(text string) tea.Cmd {
	m.turn.busy = true
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
	transcript := lipgloss.NewStyle().Padding(0, 3, 0, 1).Render(m.vp.View())
	if m.toast != "" {
		transcript = overlayToast(transcript, m.toast, m.width)
	} else if m.turn.thinking != "" {
		transcript = overlayToast(transcript, glyphs.ToolCall+" "+m.turn.thinking, m.width)
	}
	screen := transcript + "\n" + m.bottom()
	if p := m.turn.permission; p != nil {
		screen = m.r.permissionModal(*p, m.cwd, m.width)
		screen += strings.Repeat("\n", max(m.height-lipgloss.Height(screen), 0))
	}
	v := tea.NewView(screen)
	v.AltScreen = true
	v.MouseMode = tea.MouseModeCellMotion
	v.BackgroundColor = col(palette.Bg)
	v.ForegroundColor = col(screenText)
	return v
}

// bottom is everything under the transcript: the status line and the input bar.
func (m chatModel) bottom() string {
	if m.pal.kind != paletteNone {
		return paletteBox(m.pal, m.width) + "\n" + inputBox(m.width, m.editorView(), !m.navMode)
	}
	out := statusLine(m.width, m.provider, m.turn.model, m.mode, m.turn.ctxPct, m.turn.costUSD, m.git)
	if len(m.queue) > 0 {
		out += "\n" + queueChip(m.queue, m.width)
	}
	return out + "\n" + inputBox(m.width, m.editorView(), !m.navMode)
}

// editorView draws the placeholder over an empty editor with no cursor on it,
// as Textual's overlay does.
func (m chatModel) editorView() string {
	surface := lipgloss.NewStyle().Background(col(palette.Surface))
	if m.search.active {
		line := m.searchLine()
		if m.width > 8 {
			line = ansi.Truncate(line, m.width-8, "…")
		}
		return surface.Foreground(col(palette.Text)).Render(line)
	}
	if m.editor.Value() == "" {
		return surface.Foreground(col(palette.Dim)).Render(m.editor.Placeholder)
	}
	return m.editor.View()
}

func (m chatModel) working() string {
	label := "working"
	if m.turn.pendingTool != "" {
		label = "tool: " + m.turn.pendingTool
	}
	return workingLine(m.frame, label, time.Since(m.sentAt), m.turn.streamedChars/4)
}

// layout sizes the transcript to the space the bottom area leaves and keeps
// it on the newest line while following.
func (m *chatModel) layout() {
	m.vp.SetWidth(m.r.width)
	m.vp.SetHeight(max(m.height-lipgloss.Height(m.bottom()), 1))
	if len(m.blocks) == 0 && m.live == "" && !m.turn.busy {
		m.vp.SetContent(homeScreen(m.width, m.height, m.home))
		m.vp.GotoTop()
		return
	}
	parts := append([]string(nil), m.rendered...)
	if i := m.navIdx; m.navMode && i >= 0 && i < len(parts) {
		gap, body := "", parts[i]
		if rest, ok := strings.CutPrefix(body, "\n"); ok {
			gap, body = "\n", rest
		}
		parts[i] = gap + tint(body, m.r.width)
	}
	if m.trimmed > 0 {
		parts = append([]string{m.trimPlaceholder()}, parts...)
	}
	if m.live != "" {
		parts = append(parts, m.live)
	}
	if m.turn.busy {
		parts = append(parts, m.working())
	}
	content := strings.Join(parts, "\n")
	m.vp.SetContent(content)
	if m.follow {
		m.vp.GotoBottom()
	}
}

// add commits finished blocks to the transcript.
func (m *chatModel) add(blocks ...block) {
	for _, b := range blocks {
		m.blocks = append(m.blocks, b)
		m.rendered = append(m.rendered, m.renderAt(len(m.blocks)-1))
	}
	m.trim()
}

// setNav moves focus to or from the transcript; entering focuses the last block.
func (m *chatModel) setNav(on bool) {
	m.navMode, m.pendingG = on, false
	m.navIdx = -1
	if on {
		m.navSet(len(m.blocks) - 1)
	}
}

// renderAt draws block i with the blank line Textual puts before every block
// after the first unless it is joined to the one above.
func (m chatModel) renderAt(i int) string {
	b := m.blocks[i]
	body := m.r.block(b)
	if b.card != nil {
		body = m.r.toolCard(b.card, m.frame)
	}
	if i > 0 && !b.joined {
		return "\n" + body
	}
	return body
}

// rerender rebuilds every block for a new width or background.
func (m *chatModel) rerender() {
	m.r = newRenderer(m.width - transcriptInset)
	for i := range m.blocks {
		m.rendered[i] = m.renderAt(i)
	}
	m.live = m.renderLive()
}

func (m chatModel) renderLive() string {
	if m.turn.streaming == "" {
		return ""
	}
	return m.r.block(assistantBlock(m.turn.streaming))
}

func nonEmpty(parts ...string) []string {
	var out []string
	for _, p := range parts {
		if p != "" {
			out = append(out, p)
		}
	}
	return out
}

// choosePalette runs the highlighted command or inserts the highlighted path.
func (m chatModel) choosePalette() (tea.Model, tea.Cmd) {
	name := m.pal.names[m.pal.idx]
	if m.pal.kind == paletteMention {
		text := []rune(m.editor.Value())
		cursor := m.cursorOffset()
		if at, _, ok := findMentionToken(text, cursor); ok {
			m.editor.SetValue(string(text[:at]) + name + " " + string(text[cursor:]))
			m.moveCursorTo(at + len([]rune(name)) + 1)
		} else {
			m.editor.InsertString(name + " ")
		}
		m.pal, m.mentionFiles = picker{}, nil
		m.lastText = m.editor.Value()
		return m, nil
	}
	m.recentCommands = append([]string{name}, m.recentCommands...)[:min(len(m.recentCommands)+1, 10)]
	m.editor.Reset()
	line := "/" + strings.TrimLeft(name, "/")
	if m.turn.busy {
		m.queue = append(m.queue, line)
		return m, nil
	}
	cmd := m.dispatch(line)
	return m, cmd
}
