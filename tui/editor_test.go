package main

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"testing"
	"time"

	tea "charm.land/bubbletea/v2"
	voss "github.com/vosslang/voss/sdk/go"
)

func TestPromptEditorRunsWithArgumentsAndReturnsEditedText(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("fixture uses sh")
	}
	dir := t.TempDir()
	editor := filepath.Join(dir, "test editor")
	script := "#!/bin/sh\n[ \"$1\" = '--wait' ] || exit 2\ncat edited.md > \"$2\"\n"
	if err := os.WriteFile(editor, []byte(script), 0o700); err != nil {
		t.Fatal(err)
	}
	want := "edited héllo\nsecond line\n"
	if err := os.WriteFile(filepath.Join(dir, "edited.md"), []byte(want), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("EDITOR", strconv.Quote(editor)+" --wait")
	c, done, err := promptEditor(context.Background(), dir, "original prompt")
	if err != nil {
		t.Fatal(err)
	}
	path := c.Args[len(c.Args)-1]
	t.Cleanup(func() { os.Remove(path) })
	if got, err := os.ReadFile(path); err != nil || string(got) != "original prompt" {
		t.Fatalf("editor input = %q, %v", got, err)
	}
	if info, err := os.Stat(path); err != nil || info.Mode().Perm() != 0o600 {
		t.Fatalf("editor temp file should be private: %v, %v", info, err)
	}
	msg := done(c.Run()).(editorDoneMsg)
	if msg.err != nil || msg.text != want {
		t.Fatalf("editor result = %+v", msg)
	}
	if _, err := os.Stat(path); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("editor temp file remains: %v", err)
	}
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	d.typeText("original prompt")
	d.send(msg)
	if got := d.m.editor.Value(); got != want || d.m.turn.busy {
		t.Fatalf("editor should restore input without submitting, got %q", got)
	}
}

func TestEditorFailurePreservesDraftAndPasteContents(t *testing.T) {
	t.Setenv("EDITOR", filepath.Join(t.TempDir(), "missing-editor"))
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	big := strings.Repeat("line\n", 7) + "end"
	d.send(tea.PasteMsg{Content: big})
	draft := d.m.editor.Value()
	c, done, err := promptEditor(d.m.ctx, d.m.cwd, d.m.expandPastes(draft))
	if err != nil {
		t.Fatal(err)
	}
	path := c.Args[len(c.Args)-1]
	t.Cleanup(func() { os.Remove(path) })
	if got, err := os.ReadFile(path); err != nil || string(got) != big {
		t.Fatalf("editor should receive expanded paste, got %q, %v", got, err)
	}
	msg := done(c.Run()).(editorDoneMsg)
	if msg.err == nil {
		t.Fatal("missing editor should fail")
	}
	d.send(msg)
	if d.m.editor.Value() != draft || d.m.expandPastes(draft) != big {
		t.Fatal("editor failure lost the original draft or its paste")
	}
	if !strings.Contains(d.transcript(), "editor:") {
		t.Fatal("editor failure should be visible")
	}
	if _, err := os.Stat(path); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("failed editor left a temp file: %v", err)
	}
}

func TestCtrlGReportsInvalidEditorWithoutClearingInput(t *testing.T) {
	t.Setenv("EDITOR", "'unclosed")
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	d.typeText("keep this draft")
	d.send(tea.KeyPressMsg{Code: 'g', Mod: tea.ModCtrl})
	if d.m.editor.Value() != "keep this draft" || !strings.Contains(d.transcript(), "editor:") {
		t.Fatal("Ctrl+G should report invalid EDITOR and keep the draft")
	}
}

func TestCtrlGReturnsToChatAfterExternalEditor(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("fixture uses sh")
	}
	for _, tc := range []struct {
		name, editor, want string
	}{
		{"saved", `sh -c 'printf edited > "$1"' editor`, "edited"},
		{"failed", `sh -c 'exit 1' editor`, "draft"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv("EDITOR", tc.editor)
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			_, client := newFakeServer(t)
			events := make(chan voss.TypedEvent)
			defer close(events)
			m := newChatModel(ctx, client, sessionMeta{ID: "test", Cwd: t.TempDir()}, events)
			m.editor.SetValue("draft")
			var p *tea.Program
			p = tea.NewProgram(m, tea.WithContext(ctx), tea.WithInput(strings.NewReader("")), tea.WithOutput(io.Discard),
				tea.WithoutSignalHandler(), tea.WithFilter(func(_ tea.Model, msg tea.Msg) tea.Msg {
					if _, ok := msg.(editorDoneMsg); ok {
						go p.Send(tea.KeyPressMsg{Code: 'c', Mod: tea.ModCtrl})
					}
					return msg
				}))
			go p.Send(tea.KeyPressMsg{Code: 'g', Mod: tea.ModCtrl})
			final, err := p.Run()
			if err != nil {
				t.Fatal(err)
			}
			if got := final.(chatModel).editor.Value(); got != tc.want {
				t.Fatalf("input after editor = %q, want %q", got, tc.want)
			}
		})
	}
}

func TestEditingShortcutsLeavePermissionsAndTranscriptFocusAlone(t *testing.T) {
	_, client := newFakeServer(t)
	d := newDriver(t, client, make(chan voss.TypedEvent))
	d.typeText("draft")
	d.press("ctrl+u", "alt+y")
	d.m.turn.permission = &voss.PermissionUpdated{Id: "p1", ToolName: "fs_write"}
	for _, k := range []tea.KeyPressMsg{
		{Code: 'k', Mod: tea.ModCtrl}, {Code: 'g', Mod: tea.ModCtrl}, {Code: 'y', Mod: tea.ModAlt},
	} {
		d.send(k)
	}
	if d.m.editor.Value() != "draft" || d.m.turn.permission == nil {
		t.Fatal("editor shortcuts should not change a permission prompt")
	}
	d.m.turn.permission = nil
	d.press("esc")
	d.send(tea.KeyPressMsg{Code: 'u', Mod: tea.ModCtrl})
	d.send(tea.KeyPressMsg{Code: 'g', Mod: tea.ModCtrl})
	if d.m.editor.Value() != "draft" || !d.m.navMode {
		t.Fatal("editor shortcuts should not steal transcript focus")
	}
}
