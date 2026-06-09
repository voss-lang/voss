package voss

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
)

// sseMaxLineBytes caps a single SSE line so a runaway `data:` can't exhaust memory.
const sseMaxLineBytes = 1 << 20

// Events streams typed events from GET /session/:id/events. A non-200 open
// returns a *VossError. Cancelling ctx tears down the TCP read (cancelling the
// turn server-side, PROTOCOL §8) and closes the channel; no leak.
func (c *Client) Events(ctx context.Context, sessionID string) (<-chan TypedEvent, error) {
	req, err := c.newRequest(ctx, http.MethodGet, "/session/"+url.PathEscape(sessionID)+"/events", nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Accept", "text/event-stream")

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	if err := checkResponse(resp); err != nil {
		// non-2xx: checkResponse already closed the body.
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		return nil, fmt.Errorf("unexpected status %d, want 200", resp.StatusCode)
	}

	ch := make(chan TypedEvent, 32)
	go func() {
		defer resp.Body.Close()
		defer close(ch)
		parseSSE(ctx, resp.Body, ch)
	}()
	return ch, nil
}

// parseSSE accumulates `data:` lines, decodes each frame on the blank-line
// boundary, and ignores comment/event/id lines. Bad JSON or unknown types are
// skipped, not panicked.
func parseSSE(ctx context.Context, r io.Reader, ch chan<- TypedEvent) {
	sc := bufio.NewScanner(r)
	sc.Buffer(make([]byte, 0, 64*1024), sseMaxLineBytes)

	var data []string
	flush := func() bool {
		if len(data) == 0 {
			return true
		}
		payload := strings.Join(data, "\n")
		data = data[:0]

		var union EventEnvelope_Event
		if err := json.Unmarshal([]byte(payload), &union); err != nil {
			return true // tolerate malformed frame
		}
		ev, err := Decode(EventEnvelope{Event: union})
		if err != nil {
			return true // unknown type: cannot deliver on a TypedEvent channel
		}
		select {
		case ch <- ev:
			return true
		case <-ctx.Done():
			return false
		}
	}

	for sc.Scan() {
		select {
		case <-ctx.Done():
			return
		default:
		}

		line := strings.TrimRight(sc.Text(), "\r")
		switch {
		case line == "":
			if !flush() {
				return
			}
		case strings.HasPrefix(line, ":"):
			// comment / ping keepalive — ignore
		case strings.HasPrefix(line, "data:"):
			data = append(data, strings.TrimPrefix(strings.TrimPrefix(line, "data:"), " "))
		default:
			// event: / id: / other field lines — type comes from the data JSON
		}
	}
	// Trailing frame without a final blank line.
	flush()
}
