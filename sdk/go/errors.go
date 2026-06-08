package voss

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// VossError is the typed error returned by every REST and SSE call for a
// non-2xx server response. It carries the HTTP status and the `detail` string
// from the server's `{v, detail}` error body (PROTOCOL §9). It deliberately
// holds nothing else — never the request, headers, or bearer token — so it is
// safe to log.
type VossError struct {
	Status int
	Detail string
}

func (e *VossError) Error() string {
	return fmt.Sprintf("HTTP %d: %s", e.Status, e.Detail)
}

// checkResponse returns nil for a 2xx status, otherwise a *VossError carrying
// the status code and the server's `detail` field. It tolerates an empty or
// unparseable body (Detail stays ""), never panics, and does not close the
// response body for the success path (the caller owns it). Mirrors
// crates/voss-tui/src/net.rs::ok_or_detail.
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
