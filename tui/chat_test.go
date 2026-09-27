package main

import (
	"context"
	"encoding/json"
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
		case conflict:
			w.WriteHeader(http.StatusConflict)
			_, _ = w.Write([]byte(`{"detail":"a turn is already running"}`))
		case failSend && strings.HasSuffix(r.URL.Path, "/message"):
			w.WriteHeader(http.StatusUnprocessableEntity)
			_, _ = w.Write([]byte(`{"detail":"empty message"}`))
		case strings.HasSuffix(r.URL.Path, "/permission"):
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

// driver is a minimal Bubble Tea event loop: it runs commands, feeds their
// messages back into the model and keeps what the model prints to scrollback.
type driver struct {
	t       *testing.T
	m       chatModel
	msgs    chan tea.Msg
	printed []string
	quit    bool
}

func newDriver(t *testing.T, client *voss.Client, events <-chan voss.TypedEvent) *driver {
	d := &driver{t: t, m: newChatModel(context.Background(), client, "sess-1", t.TempDir(), events), msgs: make(chan tea.Msg, 1024)}
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
			if v := reflect.ValueOf(msg); v.Type().Name() == "printLineMessage" {
				d.printed = append(d.printed, v.FieldByName("messageBody").String())
				continue
			}
			d.send(msg)
		case <-deadline:
			d.t.Fatalf("timed out waiting for %s; printed:\n%s", what, strings.Join(d.printed, "\n"))
		}
	}
}

func (d *driver) transcript() string { return ansi.Strip(strings.Join(d.printed, "\n")) }

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

func TestPermissionPromptTakesOnlyItsChoices(t *testing.T) {
	f, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)

	events <- voss.PermissionUpdated{Id: "p1", ToolName: "fs_edit"}
	d.until("prompt", func() bool { return d.m.turn.permission != nil })
	d.press("x", "y")
	if d.m.turn.permission == nil || d.m.editor.Value() != "" {
		t.Fatalf("stray keys answered the prompt or reached the editor (editor %q)", d.m.editor.Value())
	}
	d.press("A")
	d.until("reply", func() bool { return len(f.requestsTo("/permission")) == 1 })
	if r := f.requestsTo("/permission")[0]; r.body["id"] != "p1" || r.body["choice"] != "A" {
		t.Fatalf("reply = %+v", r.body)
	}
	if d.m.turn.permission != nil {
		t.Fatal("prompt still open after answering")
	}

	events <- voss.PermissionUpdated{Id: "p2", ToolName: "scope_expand"}
	d.until("scope prompt", func() bool { return d.m.turn.permission != nil })
	d.press("a", "n")
	d.until("scope reply", func() bool { return len(f.requestsTo("/permission")) == 2 })
	if r := f.requestsTo("/permission")[1]; r.body["id"] != "p2" || r.body["choice"] != "n" {
		t.Fatalf("scope reply = %+v", r.body)
	}
}

func TestEscAbortsAndReturnsQueuedMessagesToEditor(t *testing.T) {
	f, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)

	d.typeText("one")
	d.press("enter")
	d.typeText("two")
	d.press("enter")
	d.press("esc")
	d.until("abort", func() bool { return len(f.requestsTo("/abort")) == 1 })
	if d.m.editor.Value() != "two" || len(d.m.queue) != 0 {
		t.Fatalf("editor = %q, queue = %v; want the queued message back in the editor", d.m.editor.Value(), d.m.queue)
	}
	events <- voss.SessionIdle{}
	d.until("idle", func() bool { return !d.m.turn.busy })
	if n := len(f.requestsTo("/message")); n != 1 {
		t.Fatalf("%d sends after abort, want only the first", n)
	}
}

func TestShiftTabCyclesModeSentWithMessage(t *testing.T) {
	f, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))

	d.press("shift+tab")
	d.typeText("go")
	d.press("enter")
	d.until("send", func() bool { return len(f.requestsTo("/message")) == 1 })
	if mode := f.requestsTo("/message")[0].body["mode"]; mode != "edit" {
		t.Fatalf("mode = %v, want edit", mode)
	}
	d.press("shift+tab", "shift+tab")
	if d.m.mode != "plan" {
		t.Fatalf("mode = %q after a full cycle, want plan", d.m.mode)
	}
}

func TestCtrlCClearsThenQuitsAndCtrlDQuitsWhenEmpty(t *testing.T) {
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))

	d.typeText("draft")
	d.press("ctrl+c")
	if d.m.editor.Value() != "" {
		t.Fatalf("editor = %q after ctrl+c", d.m.editor.Value())
	}
	d.press("ctrl+c")
	d.until("quit", func() bool { return d.quit })

	d = newDriver(t, client, make(chan voss.TypedEvent))
	d.typeText("x")
	d.press("ctrl+d")
	if d.m.editor.Value() == "" {
		t.Fatal("ctrl+d with text in the editor should not quit or clear")
	}
	d.press("ctrl+c", "ctrl+d")
	d.until("quit", func() bool { return d.quit })
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

func TestCtrlOPrintsTheLastToolArguments(t *testing.T) {
	_, client := newFakeServer(t)
	events := make(chan voss.TypedEvent)
	d := newDriver(t, client, events)

	d.press("ctrl+o")
	args := map[string]any{"path": "notes.txt"}
	events <- voss.ToolEvent{Name: "fs_read", State: "ok", Args: &args}
	d.until("tool row", func() bool { return strings.Contains(d.transcript(), "⚙ fs_read") })
	if strings.Contains(d.transcript(), "arguments") {
		t.Fatal("ctrl+o printed something before any tool ran")
	}
	d.press("ctrl+o")
	d.until("arguments", func() bool { return strings.Contains(d.transcript(), "fs_read arguments:\n  path: notes.txt") })
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
	for _, want := range []string{"› first", "hello from fake turn", "echo: first", "› second", "echo: second"} {
		i := strings.Index(out[last+1:], want)
		if i < 0 {
			t.Fatalf("%q missing or out of order in:\n%s", want, out)
		}
		last += 1 + i
	}
}
