package voss

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"
)

// spawnState holds the child-process handle for a spawned server. The attach
// path leaves Client.spawn nil; spawn.go fills this struct and Close() owns the
// teardown.
type spawnState struct {
	cmd    *exec.Cmd
	stdinW io.WriteCloser
	pid    int
}

// Client is the loopback REST/SSE client for a `voss serve` process, created by
// AttachClient (spawn == nil) or Spawn (spawn populated). Every request carries
// the bearer token via the single newRequest chokepoint.
type Client struct {
	http    *http.Client
	baseURL string
	token   string
	spawn   *spawnState
}

// AttachClient builds a Client for an already-running server at baseURL
// authenticated with token. It owns no child process (spawn stays nil), so
// Close() is a no-op for the process.
func AttachClient(baseURL, token string) *Client {
	return &Client{
		http:    &http.Client{},
		baseURL: baseURL,
		token:   token,
	}
}

// String redacts the token so a Client is safe to log.
func (c *Client) String() string {
	return fmt.Sprintf("Client{baseURL:%q, token:<redacted>, spawned:%t}", c.baseURL, c.spawn != nil)
}

// Close releases resources. No-op for an attach client. For a spawned client it
// closes the stdin heartbeat (firing the server's stdin-EOF supervision), kills
// the child, and reaps it — no orphan. Idempotent once reaped.
func (c *Client) Close() error {
	if c.spawn == nil {
		return nil
	}
	s := c.spawn
	if s.cmd == nil || s.cmd.ProcessState != nil {
		return nil // already reaped
	}
	if s.stdinW != nil {
		_ = s.stdinW.Close()
	}
	if s.cmd.Process != nil {
		_ = s.cmd.Process.Kill()
	}
	_ = s.cmd.Wait() // reaps the zombie; the post-Kill error is expected and ignored
	return nil
}

// newRequest is the single chokepoint that attaches Authorization: Bearer
// <token> to every request — REST and the SSE GET both route through here. No
// other site sets the Authorization header.
func (c *Client) newRequest(ctx context.Context, method, path string, body io.Reader) (*http.Request, error) {
	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+c.token)
	return req, nil
}

// do sends req, maps non-2xx to a typed VossError (checkResponse), asserts the
// exact expected success status, and decodes the JSON body into out (nil to
// discard). It closes the body exactly once.
func (c *Client) do(req *http.Request, want int, out any) error {
	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	if err := checkResponse(resp); err != nil {
		// checkResponse closed the body on the error path.
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != want {
		_, _ = io.Copy(io.Discard, resp.Body)
		return fmt.Errorf("unexpected status %d, want %d", resp.StatusCode, want)
	}
	if out != nil {
		return json.NewDecoder(resp.Body).Decode(out)
	}
	_, _ = io.Copy(io.Discard, resp.Body)
	return nil
}

// getJSON issues a bearer-authenticated GET and decodes the response into out.
func (c *Client) getJSON(ctx context.Context, path string, want int, out any) error {
	req, err := c.newRequest(ctx, http.MethodGet, path, nil)
	if err != nil {
		return err
	}
	return c.do(req, want, out)
}

// sendJSON issues a bearer-authenticated method request with an optional JSON
// body (in) and decodes the response into out (both may be nil).
func (c *Client) sendJSON(ctx context.Context, method, path string, in, out any, want int) error {
	var body io.Reader
	hasBody := in != nil
	if hasBody {
		b, err := json.Marshal(in)
		if err != nil {
			return err
		}
		body = bytes.NewReader(b)
	}
	req, err := c.newRequest(ctx, method, path, body)
	if err != nil {
		return err
	}
	if hasBody {
		req.Header.Set("Content-Type", "application/json")
	}
	return c.do(req, want, out)
}
