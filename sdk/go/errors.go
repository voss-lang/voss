package voss

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// VossError is the typed error for a non-2xx server response. It carries the
// HTTP status and the `detail` from the server's `{v, detail}` body (PROTOCOL
// §9) and nothing else — never the request, headers, or token — so it is safe
// to log.
type VossError struct {
	Status int
	Detail string
}

func (e *VossError) Error() string {
	return fmt.Sprintf("HTTP %d: %s", e.Status, e.Detail)
}

// checkResponse returns nil for 2xx, else a *VossError with the status and the
// server's `detail`. It tolerates an empty/unparseable body (Detail ""), never
// panics, and leaves the body open on the success path (caller owns it).
// Mirrors voss-tui net.rs::ok_or_detail.
func checkResponse(resp *http.Response) error {
	if resp.StatusCode/100 == 2 {
		return nil
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	var payload struct {
		Detail string `json:"detail"`
	}
	_ = json.Unmarshal(body, &payload)
	return &VossError{Status: resp.StatusCode, Detail: payload.Detail}
}
