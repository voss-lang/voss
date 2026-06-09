package voss

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"time"
)

// Handshake is the one-line JSON `voss serve` prints after binding its port:
// {"v":1,"port":51234,"token":"..."}. Token is a per-process secret.
type Handshake struct {
	V     int    `json:"v"`
	Port  uint16 `json:"port"`
	Token string `json:"token"`
}

// baseURL is the loopback REST/SSE root for the handshake's port.
func (h Handshake) baseURL() string {
	return fmt.Sprintf("http://127.0.0.1:%d", h.Port)
}

// readHandshake scans r for the first line that parses as a Handshake with a
// non-empty token, ignoring preceding non-JSON output (e.g. uvicorn logs). It
// errors on EOF before a handshake, and on timeout if none arrives in time.
// Mirrors voss-tui server.rs handshake loop.
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
