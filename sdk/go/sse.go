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

// sseMaxLineBytes bounds a single SSE field line so a malformed/never-ending
// `data:` line cannot exhaust memory. 1 MiB exceeds any real event.
const sseMaxLineBytes = 1 << 20

// Events opens GET /session/:id/events and delivers typed events on the returned
// channel. The request carries the bearer header and Accept: text/event-stream;
// a non-200 open returns a *VossError before any channel is created.
//
// One goroutine hand-parses SSE frames and decodes each through Decode().
// Cancelling ctx (or the server closing the stream) tears down the TCP read —
// cancelling the in-flight turn server-side (disconnect-cancels, PROTOCOL §8) —
// and closes the channel. resp.Body.Close() and close(ch) are deferred, so no
// goroutine or connection leak.
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

// parseSSE reads SSE frames from r and sends decoded typed events to ch until
// the context is cancelled or the stream ends. It accumulates `data:` lines per
// frame, decodes the joined payload on the blank-line boundary, and ignores
// `:` comment lines (sse-starlette ping keepalives), `event:` lines (the type
// is read from the data JSON), and `id:` lines. Malformed JSON or an unknown
// event type is skipped (not deliverable on a TypedEvent channel) rather than
// panicking.
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
