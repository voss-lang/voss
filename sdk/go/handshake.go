package voss

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"time"
)

// Handshake is the one-line JSON the `voss serve` process prints on stdout
// immediately after binding its ephemeral loopback port:
//
//	{"v":1,"port":51234,"token":"<url-safe-token>"}
//
// (voss/harness/server/serve.py). Token is an ephemeral per-process secret.
type Handshake struct {
	V     int    `json:"v"`
	Port  uint16 `json:"port"`
	Token string `json:"token"`
}

// baseURL is the loopback REST/SSE root for the handshake's port. Used by the
// spawn constructor (Plan 05) to build a Client from a spawned server.
func (h Handshake) baseURL() string {
	return fmt.Sprintf("http://127.0.0.1:%d", h.Port)
}

// readHandshake scans r line by line for the first line that parses as a
// Handshake with a non-empty token, ignoring any preceding non-JSON output
// (e.g. uvicorn startup logs). It returns a typed error if the reader reaches
// EOF before a handshake, and a timeout error if none arrives within timeout.
// Mirrors crates/voss-tui/src/server.rs handshake loop.
func readHandshake(r io.Reader, timeout time.Duration) (Handshake, error) {
	type result struct {
		h   Handshake
		err error
	}
	ch := make(chan result, 1)
	go func() {
		sc := bufio.NewScanner(r)
		for sc.Scan() {
			var h Handshake
			if err := json.Unmarshal(sc.Bytes(), &h); err == nil && h.Token != "" {
				ch <- result{h: h}
				return
			}
		}
		if err := sc.Err(); err != nil {
			ch <- result{err: err}
			return
		}
		ch <- result{err: errors.New("server exited before handshake")}
	}()

	select {
	case res := <-ch:
		return res.h, res.err
	case <-time.After(timeout):
		return Handshake{}, errors.New("handshake timeout")
	}
}
