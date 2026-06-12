// E4 Go consumer subprogram: public-API-only (AttachClient/Events/PermissionReply).
// The Python eval runner owns the serve lifecycle and passes coordinates via
// env — never Spawn (interpreterPath resolves .venv/bin/python relative to CWD).
// No per-runtime scoring: emits one structured-JSON line; the runner scores
// via the single E1 substrate.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	voss "github.com/vosslang/voss/sdk/go"
)

type result struct {
	Surface           string   `json:"surface"`
	SessionID         string   `json:"session_id"`
	Final             string   `json:"final"`
	SawPermissionGate bool     `json:"saw_permission_gate"`
	CostUSD           float64  `json:"cost_usd"`
	EventTypesSeen    []string `json:"event_types_seen"`
}

func fatal(err error) {
	if err != nil {
		fmt.Fprintf(os.Stderr, "{\"error\": %q}\n", err.Error())
		os.Exit(1)
	}
}

// eventType recovers the wire discriminator from a decoded event via its
// serialized `type` field (the Go SDK keeps eventType() unexported).
func eventType(ev voss.TypedEvent) string {
	b, err := json.Marshal(ev)
	if err != nil {
		return fmt.Sprintf("%T", ev)
	}
	var tagged struct {
		Type string `json:"type"`
	}
	if json.Unmarshal(b, &tagged) == nil && tagged.Type != "" {
		return tagged.Type
	}
	return fmt.Sprintf("%T", ev)
}

func main() {
	baseURL := os.Getenv("VOSS_BASE_URL")
	if baseURL == "" {
		fmt.Fprintln(os.Stderr, `{"error": "VOSS_BASE_URL required"}`)
		os.Exit(2)
	}
	cwd := os.Getenv("VOSS_CWD")
	if cwd == "" {
		cwd = "."
	}
	mode := os.Getenv("VOSS_MODE")
	if mode == "" {
		mode = "plan"
	}
	// Plan 07 drives Deny through this same file with VOSS_PERMISSION_CHOICE=d.
	choice := os.Getenv("VOSS_PERMISSION_CHOICE")
	if choice == "" {
		choice = "a"
	}

	// 120s ceiling so a stuck stream cannot hang the process; cancel also
	// closes the Events channel (sse.go tears down the TCP read on ctx done).
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	c := voss.AttachClient(baseURL, os.Getenv("VOSS_TOKEN"))
	defer c.Close() // no-op for attach; keeps the no-orphan idiom

	id, err := c.CreateSession(ctx, cwd)
	fatal(err)
	// Open the stream BEFORE posting so the turn is observed from the start.
	ch, err := c.Events(ctx, id)
	fatal(err)
	fatal(c.PostMessage(ctx, id, os.Getenv("VOSS_PROMPT"), mode))

	res := result{Surface: "sdk:go", SessionID: id, EventTypesSeen: []string{}}
loop:
	for ev := range ch {
		res.EventTypesSeen = append(res.EventTypesSeen, eventType(ev))
		switch e := ev.(type) {
		case voss.PermissionUpdated:
			res.SawPermissionGate = true
			_, err := c.PermissionReply(ctx, id, e.Id, choice)
			fatal(err)
		case voss.FinalEvent:
			res.Final = e.Text
		case voss.SessionIdle:
			cancel() // close the channel's TCP read; no goroutine left ranging
			break loop
		}
	}

	if cost, err := c.Cost(context.Background(), id); err == nil {
		res.CostUSD = cost.TotalUsd
	}
	out, err := json.Marshal(res)
	fatal(err)
	fmt.Println(string(out))
}
