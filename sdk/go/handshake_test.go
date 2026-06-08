package voss

import "testing"

// TestHandshakeParse will assert that readHandshake scans the server's stdout
// for the one-line JSON handshake {"v","port","token"}, ignoring any preceding
// non-JSON lines, and times out cleanly when no handshake arrives. RED until
// Plan 03 (V13.3-03) lands handshake.go.
func TestHandshakeParse(t *testing.T) {
	// TODO(V13.3-03): feed a reader with a leading log line + a valid handshake
	// JSON line to readHandshake() and assert Handshake{V,Port,Token} parses;
	// assert a timeout error when the reader yields no handshake.
	t.Skip("RED: readHandshake/Handshake implemented in Plan 03 (V13.3-03)")
}
