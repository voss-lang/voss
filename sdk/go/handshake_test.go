package voss

import (
	"io"
	"strings"
	"testing"
	"time"
)

// TestHandshakeParse covers scan-until-parse past leading noise, EOF before a
// handshake, and the timeout path; plus AttachClient's base-URL/token/nil-spawn
// invariants.
func TestHandshakeParse(t *testing.T) {
	t.Run("scan past noise", func(t *testing.T) {
		r := strings.NewReader("INFO: uvicorn started\n{\"v\":1,\"port\":51234,\"token\":\"abc\"}\n")
		h, err := readHandshake(r, 2*time.Second)
		if err != nil {
			t.Fatalf("readHandshake error: %v", err)
		}
		if h.V != 1 || h.Port != 51234 || h.Token != "abc" {
			t.Fatalf("Handshake = %+v, want {1,51234,abc}", h)
		}
		if got := h.baseURL(); got != "http://127.0.0.1:51234" {
			t.Fatalf("baseURL = %q, want http://127.0.0.1:51234", got)
		}
	})

	t.Run("eof before handshake", func(t *testing.T) {
		r := strings.NewReader("INFO: starting up\nstill no handshake\n")
		_, err := readHandshake(r, 2*time.Second)
		if err == nil {
			t.Fatal("expected error on EOF before handshake, got nil")
		}
		if !strings.Contains(err.Error(), "before handshake") {
			t.Fatalf("error = %v, want 'server exited before handshake'", err)
		}
	})

	t.Run("timeout", func(t *testing.T) {
		// A pipe with no writer blocks the scanner; the timeout must fire.
		pr, pw := io.Pipe()
		defer pw.Close()
		_, err := readHandshake(pr, 50*time.Millisecond)
		if err == nil || !strings.Contains(err.Error(), "timeout") {
			t.Fatalf("expected timeout error, got %v", err)
		}
	})
}

// TestAttachClient asserts AttachClient sets baseURL/token, owns no child
// (spawn nil), and Close() is a no-op.
func TestAttachClient(t *testing.T) {
	c := AttachClient("http://127.0.0.1:51234", "tok-123")
	if c.baseURL != "http://127.0.0.1:51234" || c.token != "tok-123" {
		t.Fatalf("client = {%q,%q}, want base/token set", c.baseURL, c.token)
	}
	if c.spawn != nil {
		t.Fatal("attach client must own no child (spawn != nil)")
	}
	if err := c.Close(); err != nil {
		t.Fatalf("Close() on attach client = %v, want nil", err)
	}
	if strings.Contains(c.String(), "tok-123") {
		t.Fatalf("String() leaked token: %q", c.String())
	}
}
