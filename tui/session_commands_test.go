package main

import (
	"context"
	"strings"
	"testing"
	"time"

	voss "github.com/vosslang/voss/sdk/go"
)

func TestBudgetAndWhyAgainstFakeTurnServer(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
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
	streamCtx, stopStream := context.WithCancel(ctx)
	defer stopStream()
	events, err := client.Events(streamCtx, id)
	if err != nil {
		t.Fatal(err)
	}
	d := newDriver(t, client, events)
	d.m.sessionID = id
	d.until("session command catalog", func() bool {
		_, budget := d.m.lookupCommand("/budget")
		_, why := d.m.lookupCommand("/why")
		return budget && why
	})
	d.typeText("/bud")
	if d.m.pal.kind != paletteSlash || len(d.m.pal.names) != 1 || d.m.pal.names[0] != "/budget" {
		t.Fatalf("budget absent from palette: %+v", d.m.pal)
	}
	d.press("esc")
	d.m.editor.Reset()

	submit := func(command, want string) {
		t.Helper()
		d.typeText(command)
		d.press("enter")
		d.until(command, func() bool {
			return d.m.commanding == "" && strings.Contains(d.transcript(), want)
		})
	}
	submit("/why", "no plan yet — run a turn first")
	submit("/budget $5", "budget: $5.00 (used $0.0000)")
	submit("/cost", "session cost: $0.0000 / $5.00 (0.0%)")
	submit("/budget nan", "budget must be finite and non-negative")
	cost, err := client.Cost(ctx, id)
	if err != nil || cost.BudgetUsd == nil || *cost.BudgetUsd != 5 {
		t.Fatalf("invalid budget changed setting: %+v, %v", cost, err)
	}
	if d.m.turn.busy || strings.Contains(d.transcript(), "echo:") {
		t.Fatal("session command started a model turn")
	}
	d.typeText("run a synthetic task")
	d.press("enter")
	d.until("fake turn", func() bool {
		return !d.m.turn.busy && strings.Contains(d.transcript(), "echo: run a synthetic task")
	})
	submit("/why", "rationale: fake turn")
	if !strings.Contains(d.transcript(), "confidence: 0.90") {
		t.Fatal("last plan confidence missing")
	}
	submit("/budget 0", "budget: cleared (unbounded)")
	cost, err = client.Cost(ctx, id)
	if err != nil || cost.BudgetUsd != nil {
		t.Fatalf("budget was not cleared: %+v, %v", cost, err)
	}
}
