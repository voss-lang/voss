package voss

import "testing"

// TestIntegrationSSEOrdering will assert the SSE consumer delivers the
// VOSS_SERVE_FAKE_TURN canned sequence in order — server.connected first,
// stream.delta present, session.idle last — over <-chan TypedEvent. RED until
// Plan 04 (V13.3-04) lands sse.go.
func TestIntegrationSSEOrdering(t *testing.T) {
	// TODO(V13.3-04): post a message, range over Events(ctx, sid), assert the
	// 8-event fake-turn order (RESEARCH §VOSS_SERVE_FAKE_TURN).
	t.Skip("RED: SSE consumer implemented in Plan 04 (V13.3-04)")
}

// TestIntegrationSSECancel will assert cancelling the context tears down the
// SSE GET (disconnect-cancels, PROTOCOL §8), closes the channel, and leaks no
// goroutine. RED until Plan 04 (V13.3-04).
func TestIntegrationSSECancel(t *testing.T) {
	// TODO(V13.3-04): cancel ctx mid-stream, assert the channel closes and no
	// goroutine leak (http.NewRequestWithContext + defer close(ch)).
	t.Skip("RED: SSE context-cancel implemented in Plan 04 (V13.3-04)")
}
