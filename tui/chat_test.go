package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"sync"
	"testing"
	"time"
	"unicode"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/x/ansi"
	voss "github.com/vosslang/voss/sdk/go"
)

type request struct {
	path string
	body map[string]any
}

// fakeServer answers the REST calls the chat model makes and records them.
type fakeServer struct {
	mu        sync.Mutex
	reqs      []request
	conflicts int
	failSend  bool
}

func newFakeServer(t *testing.T) (*fakeServer, *voss.Client) {
	f := &fakeServer{}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		raw, _ := io.ReadAll(r.Body)
		var body map[string]any
		_ = json.Unmarshal(raw, &body)
		f.mu.Lock()
		f.reqs = append(f.reqs, request{r.URL.Path, body})
		conflict := strings.HasSuffix(r.URL.Path, "/message") && f.conflicts > 0
		if conflict {
			f.conflicts--
		}
		failSend := f.failSend
		f.mu.Unlock()
		switch {
		case r.URL.Path == "/commands":
			_, _ = w.Write([]byte(`{"v":1,"commands":[]}`))
		case conflict:
			w.WriteHeader(http.StatusConflict)
			_, _ = w.Write([]byte(`{"detail":"a turn is already running"}`))
		case failSend && strings.HasSuffix(r.URL.Path, "/message"):
			w.WriteHeader(http.StatusUnprocessableEntity)
			_, _ = w.Write([]byte(`{"detail":"empty message"}`))
		case strings.HasSuffix(r.URL.Path, "/permission"), strings.HasSuffix(r.URL.Path, "/diff"):
			_, _ = w.Write([]byte(`{"v":1,"status":"ok"}`))
		default:
			w.WriteHeader(http.StatusAccepted)
			_, _ = w.Write([]byte(`{}`))
		}
	}))
	t.Cleanup(srv.Close)
	return f, voss.AttachClient(srv.URL, "t")
}

func (f *fakeServer) requestsTo(suffix string) []request {
	f.mu.Lock()
	defer f.mu.Unlock()
	var out []request
	for _, r := range f.reqs {
		if strings.HasSuffix(r.path, suffix) {
			out = append(out, r)
		}
	}
	return out
}

// driver is a minimal Bubble Tea event loop: it runs commands and feeds
// their messages back into the model.
type driver struct {
	t         *testing.T
	m         chatModel
	msgs      chan tea.Msg
	quit      bool
	clipboard string
}

func newDriver(t *testing.T, client *voss.Client, events <-chan voss.TypedEvent) *driver {
	d := &driver{t: t, m: newChatModel(context.Background(), client, sessionMeta{ID: "sess-1", Cwd: t.TempDir()}, events), msgs: make(chan tea.Msg, 1024)}
	d.run(d.m.Init())
	return d
}

func (d *driver) run(cmd tea.Cmd) {
	if cmd == nil {
		return
	}
	go func() { d.post(cmd()) }()
}

// post expands tea.Batch and tea.Sequence results, whose message types are slices of commands.
func (d *driver) post(msg tea.Msg) {
	if msg == nil {
		return
	}
	v := reflect.ValueOf(msg)
	if v.Kind() == reflect.Slice && v.Type().Elem() == reflect.TypeOf(tea.Cmd(nil)) {
		for i := 0; i < v.Len(); i++ {
			d.run(v.Index(i).Interface().(tea.Cmd))
		}
		return
	}
	d.msgs <- msg
}

func (d *driver) send(msg tea.Msg) {
	model, cmd := d.m.Update(msg)
	d.m = model.(chatModel)
	d.run(cmd)
}

func (d *driver) press(keys ...string) {
	for _, k := range keys {
		d.send(key(k))
	}
}

func (d *driver) typeText(s string) {
	for _, r := range s {
		d.send(key(string(r)))
	}
}

// until processes messages until cond holds, failing after a deadline.
func (d *driver) until(what string, cond func() bool) {
	d.t.Helper()
	deadline := time.After(10 * time.Second)
	poll := time.NewTicker(10 * time.Millisecond)
	defer poll.Stop()
	for !cond() {
		select {
		case <-poll.C:
		case msg := <-d.msgs:
			switch msg.(type) {
			case tea.QuitMsg:
				d.quit = true
				continue
			}
			if v := reflect.ValueOf(msg); v.Type().Name() == "setClipboardMsg" {
				d.clipboard = v.String()
				continue
			}
			d.send(msg)
		case <-deadline:
			d.t.Fatalf("timed out waiting for %s; transcript:\n%s", what, d.transcript())
		}
	}
}

func (d *driver) transcript() string { return ansi.Strip(strings.Join(d.m.rendered, "\n")) }

func key(s string) tea.KeyPressMsg {
	switch s {
	case "enter":
		return tea.KeyPressMsg{Code: tea.KeyEnter}
	case "esc":
		return tea.KeyPressMsg{Code: tea.KeyEscape}
	case "shift+tab":
		return tea.KeyPressMsg{Code: tea.KeyTab, Mod: tea.ModShift}
	case "ctrl+c":
		return tea.KeyPressMsg{Code: 'c', Mod: tea.ModCtrl}
	case "ctrl+d":
		return tea.KeyPressMsg{Code: 'd', Mod: tea.ModCtrl}
	case "ctrl+o":
		return tea.KeyPressMsg{Code: 'o', Mod: tea.ModCtrl}
	}
	r := []rune(s)[0]
	k := tea.KeyPressMsg{Code: unicode.ToLower(r), Text: s}
	if unicode.IsUpper(r) {
		k.Mod = tea.ModShift
	}
	return k
}

func TestEnterDuringTurnQueuesAndSendsAfterIdleInOrder(t *testing.T) {
	f, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)

	d.typeText("one")
	d.press("enter")
	d.until("first send", func() bool { return len(f.requestsTo("/message")) == 1 })
	d.typeText("two")
	d.press("enter")
	if len(d.m.queue) != 1 || len(f.requestsTo("/message")) != 1 {
		t.Fatalf("queue = %v, sends = %d; want the second message queued", d.m.queue, len(f.requestsTo("/message")))
	}

	events <- voss.SessionIdle{}
	d.until("queued send", func() bool { return len(f.requestsTo("/message")) == 2 })
	sends := f.requestsTo("/message")
	if text(sends[0]) != "one" || text(sends[1]) != "two" || sends[1].body["mode"] != "plan" {
		t.Fatalf("sends = %+v", sends)
	}
	if !d.m.turn.busy || len(d.m.queue) != 0 {
		t.Fatalf("after dequeue busy = %v, queue = %v", d.m.turn.busy, d.m.queue)
	}
}

func TestQueuedLinesShowAChipAndReplayInOrderAfterTheTurn(t *testing.T) {
	f, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)

	d.typeText("first")
	d.press("enter")
	d.typeText("/mode edit")
	d.press("enter")
	d.typeText(`say "hi"`)
	d.press("enter")
	if chip := ansi.Strip(d.m.bottom()); !strings.Contains(chip, `queued (2): "say "hi""`) {
		t.Fatalf("bottom area:\n%s", chip)
	}
	if strings.Contains(d.transcript(), "mode: edit") {
		t.Fatal("a slash command typed during a turn ran before the turn ended")
	}

	events <- voss.SessionIdle{}
	d.until("queued send", func() bool { return len(f.requestsTo("/message")) == 2 })
	sent := f.requestsTo("/message")[1]
	if text(sent) != `say "hi"` || sent.body["mode"] != "edit" {
		t.Fatalf("second send = %+v; want the queued /mode applied first", sent.body)
	}
	if !strings.Contains(d.transcript(), "mode: edit") || strings.Contains(ansi.Strip(d.m.bottom()), "queued") {
		t.Fatal("the queue did not drain")
	}
}

func TestConflictPutsMessageBackAndRetriesAfterIdle(t *testing.T) {
	f, client := newFakeServer(t)
	f.conflicts = 1
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)

	d.typeText("hi")
	d.press("enter")
	d.until("requeue on 409", func() bool { return len(d.m.queue) == 1 })
	if !d.m.turn.busy {
		t.Fatal("a 409 means a turn is running; the client should show busy")
	}
	events <- voss.SessionIdle{}
	d.until("retry", func() bool { return len(f.requestsTo("/message")) == 2 })
	if got := text(f.requestsTo("/message")[1]); got != "hi" {
		t.Fatalf("retried %q, want hi", got)
	}
}

func TestSendFailureShowsServerDetailAndClearsBusy(t *testing.T) {
	f, client := newFakeServer(t)
	f.failSend = true
	d := newDriver(t, client, make(chan voss.TypedEvent))

	d.typeText("hi")
	d.press("enter")
	d.until("error printed", func() bool { return strings.Contains(d.transcript(), "send: empty message") })
	if d.m.turn.busy {
		t.Fatal("a rejected send left the client busy")
	}
}

func TestPermissionModalTakesOnlyItsChoices(t *testing.T) {
	f, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)

	events <- voss.PermissionUpdated{Id: "p1", ToolName: "fs_edit"}
	d.until("prompt", func() bool { return d.m.turn.permission != nil })
	if view := ansi.Strip(d.m.View().Content); !strings.HasPrefix(view, "Permission required\n\nTool fs_edit wants to modify .") {
		t.Fatalf("modal screen:\n%s", view)
	}
	d.press("x", "y")
	if d.m.turn.permission == nil || d.m.editor.Value() != "" {
		t.Fatalf("stray keys answered the prompt or reached the editor (editor %q)", d.m.editor.Value())
	}
	d.press("A")
	d.until("reply", func() bool { return len(f.requestsTo("/permission")) == 1 })
	if r := f.requestsTo("/permission")[0]; r.body["id"] != "p1" || r.body["choice"] != "A" {
		t.Fatalf("reply = %+v", r.body)
	}

	events <- voss.PermissionUpdated{Id: "p2", ToolName: "shell_run"}
	d.until("second prompt", func() bool { return d.m.turn.permission != nil })
	d.press("esc")
	d.until("esc denies", func() bool { return len(f.requestsTo("/permission")) == 2 })
	if r := f.requestsTo("/permission")[1]; r.body["choice"] != "d" {
		t.Fatalf("esc replied %v, want d", r.body["choice"])
	}

	args := map[string]any{"target": "../other"}
	events <- voss.PermissionUpdated{Id: "p3", ToolName: "scope_expand", Args: &args}
	d.until("scope prompt", func() bool { return d.m.turn.permission != nil })
	d.press("x", "a")
	d.until("scope reply", func() bool { return len(f.requestsTo("/permission")) == 3 })
	if r := f.requestsTo("/permission")[2]; r.body["id"] != "p3" || r.body["choice"] != "always" {
		t.Fatalf("scope reply = %+v, want always: the server denies a bare a", r.body)
	}
}

func TestCtrlCClearsTheQueueAndAbortsTheTurn(t *testing.T) {
	f, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)

	d.typeText("one")
	d.press("enter")
	d.typeText("two")
	d.press("enter")
	d.press("esc")
	if len(f.requestsTo("/abort")) != 0 || len(d.m.queue) != 1 {
		t.Fatal("esc during a turn should do nothing, as in Textual")
	}
	d.press("ctrl+c")
	d.until("abort", func() bool { return len(f.requestsTo("/abort")) == 1 })
	if len(d.m.queue) != 0 || d.quit {
		t.Fatalf("queue = %v, quit = %v; want the queue cleared and the app still running", d.m.queue, d.quit)
	}
	events <- voss.SessionIdle{}
	d.until("idle", func() bool { return !d.m.turn.busy })
	if n := len(f.requestsTo("/message")); n != 1 {
		t.Fatalf("%d sends after the abort, want only the first", n)
	}
}

func TestCtrlCExitsWhenIdle(t *testing.T) {
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	d.typeText("draft")
	d.press("ctrl+c")
	d.until("quit", func() bool { return d.quit })
}

func TestModeCommandSetsTheModeSentWithMessages(t *testing.T) {
	f, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))

	for _, line := range []string{"/mode", "/mode auto", "/mode nope", "/mode edit"} {
		d.typeText(line)
		d.press("enter")
	}
	out := d.transcript()
	for _, want := range []string{
		"system\n    mode: plan",
		"⚠ escalating to auto requires --confirm (e.g. /mode auto --confirm)",
		"⚠ mode must be plan|edit|auto|observe",
		"system\n    mode: edit",
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("missing %q in:\n%s", want, out)
		}
	}
	d.typeText("go")
	d.press("enter")
	d.until("send", func() bool { return len(f.requestsTo("/message")) == 1 })
	if mode := f.requestsTo("/message")[0].body["mode"]; mode != "edit" {
		t.Fatalf("mode = %v, want edit", mode)
	}
}

func TestUnknownCommandWarnsLikeTextual(t *testing.T) {
	f, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	d.typeText("/nope x")
	d.press("enter")
	if !strings.Contains(d.transcript(), "⚠ unknown command: /nope x. /help for list.") || len(f.requestsTo("/message")) != 0 {
		t.Fatalf("transcript:\n%s", d.transcript())
	}
}

func TestTabAndEscMoveFocusBetweenInputAndTranscript(t *testing.T) {
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	d.press("esc")
	if !d.m.navMode {
		t.Fatal("esc when idle should focus the transcript")
	}
	d.press("x")
	if d.m.navMode || d.m.editor.Value() != "x" {
		t.Fatalf("a printable key should return to the input and type it; editor %q", d.m.editor.Value())
	}
	d.press("tab")
	if !d.m.navMode {
		t.Fatal("tab should move focus to the transcript")
	}
	d.press("i")
	if d.m.navMode || d.m.editor.Value() != "x" {
		t.Fatal("i should return to the input without typing")
	}
}

func TestClosedStreamIsReportedAndSendsAreHeld(t *testing.T) {
	f, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)
	close(events)
	d.until("error", func() bool { return strings.Contains(d.transcript(), "lost the connection") })

	d.typeText("hi")
	d.press("enter")
	d.until("offline notice", func() bool { return strings.Contains(d.transcript(), "not connected") })
	if n := len(f.requestsTo("/message")); n != 0 || d.m.editor.Value() != "hi" {
		t.Fatalf("sends = %d, editor = %q; want nothing sent and the text kept", n, d.m.editor.Value())
	}
}

func TestStreamedMarkdownRendersLiveThenCommits(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent, 4)
	d := newDriver(t, client, events)

	events <- voss.StreamDelta{Text: "some **bold** "}
	events <- voss.StreamDelta{Text: strings.Repeat("words ", 20)}
	d.until("live render", func() bool { return strings.Contains(ansi.Strip(d.m.live), "some bold words") })
	if strings.Contains(d.m.live, "**") {
		t.Fatalf("live text is not rendered as markdown: %q", ansi.Strip(d.m.live))
	}

	d.send(tea.WindowSizeMsg{Width: 40, Height: 20})
	for _, line := range strings.Split(d.m.live, "\n") {
		if w := ansi.StringWidth(line); w > 40 {
			t.Fatalf("live line is %d columns after resizing to 40", w)
		}
	}

	events <- voss.StreamFinalize{Role: "assistant"}
	d.until("commit", func() bool { return strings.Contains(d.transcript(), "some bold words") })
	if d.m.live != "" {
		t.Fatalf("live area still shows %q after finalize", ansi.Strip(d.m.live))
	}
}

func TestEditPromptShowsTheWordDiff(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)

	args := map[string]any{"path": "notes.txt", "old": "the old value", "new": "the new value"}
	events <- voss.PermissionUpdated{Id: "p1", ToolName: "fs_edit", Args: &args}
	d.until("prompt", func() bool { return d.m.turn.permission != nil })
	view := d.m.View().Content
	if !strings.Contains(view, styleDel.Render("old")) || !strings.Contains(view, styleAdd.Render("new")) {
		t.Fatalf("prompt has no word diff:\n%s", ansi.Strip(view))
	}
}

func TestFullScreenFillsTheWindowAndFollowsTheTail(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent, 64)
	d := newDriver(t, client, events)
	d.send(tea.WindowSizeMsg{Width: 60, Height: 12})

	for i := range 30 {
		events <- voss.WarningEvent{Message: fmt.Sprintf("line %d", i)}
	}
	d.until("30 lines", func() bool { return strings.Contains(d.transcript(), "line 29") })
	view := d.m.View()
	if !view.AltScreen || strings.Count(view.Content, "\n")+1 != 12 {
		t.Fatalf("alt screen %v, %d lines; want the full 12-line window", view.AltScreen, strings.Count(view.Content, "\n")+1)
	}
	if !d.m.vp.AtBottom() || !strings.Contains(ansi.Strip(view.Content), "line 29") {
		t.Fatal("the newest line is not on screen")
	}

	d.press("pgup")
	offset := d.m.vp.YOffset()
	events <- voss.WarningEvent{Message: "arrives while scrolled up"}
	d.until("new line", func() bool { return strings.Contains(d.transcript(), "arrives while scrolled up") })
	if d.m.vp.YOffset() != offset {
		t.Fatalf("scrolled from %d to %d while the user was reading", offset, d.m.vp.YOffset())
	}

	events <- voss.UserEvent{Task: "next question"}
	d.until("user block", func() bool { return strings.Contains(d.transcript(), "next question") })
	if !d.m.vp.AtBottom() {
		t.Fatal("a new user message did not return to the bottom")
	}
}

func text(r request) string {
	parts, _ := r.body["parts"].([]any)
	if len(parts) == 0 {
		return ""
	}
	p, _ := parts[0].(map[string]any)
	s, _ := p["text"].(string)
	return s
}

// testExecutable resolves the server like the SDK tests: VOSS_BIN, else the repo's .venv.
func testExecutable(t *testing.T) string {
	if v := os.Getenv("VOSS_BIN"); v != "" {
		return v
	}
	p, _ := filepath.Abs(filepath.Join("..", ".venv", "bin", "voss"))
	if _, err := os.Stat(p); err != nil {
		t.Skip("no VOSS_BIN or repo .venv/bin/voss")
	}
	return p
}

func TestTwoQuickMessagesAgainstFakeTurnServer(t *testing.T) {
	ctx := context.Background()
	client, err := voss.Spawn(ctx, voss.LaunchOptions{
		Executable: testExecutable(t),
		Cwd:        t.TempDir(),
		Env:        map[string]string{"VOSS_SERVE_FAKE_TURN": "1"},
	})
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()
	id, err := client.CreateSession(ctx, voss.SessionOptions{})
	if err != nil {
		t.Fatal(err)
	}
	streamCtx, cancel := context.WithCancel(ctx)
	defer cancel()
	events, err := client.Events(streamCtx, id)
	if err != nil {
		t.Fatal(err)
	}
	d := newDriver(t, client, events)
	d.m.sessionID = id

	d.typeText("first")
	d.press("enter")
	d.typeText("second")
	d.press("enter")
	d.until("both turns", func() bool {
		return strings.Contains(d.transcript(), "echo: second") && !d.m.turn.busy
	})

	out := d.transcript()
	last := -1
	for _, want := range []string{"❯ first", "hello from fake turn", "echo: first", "❯ second", "echo: second"} {
		i := strings.Index(out[last+1:], want)
		if i < 0 {
			t.Fatalf("%q missing or out of order in:\n%s", want, out)
		}
		last += 1 + i
	}
}
