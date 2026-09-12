package voss

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// VossError is the typed error for a non-2xx response: HTTP status + the
// server's `detail` (9), nothing else, so it is safe to log.
type VossError struct {
	Status int
	Detail string
}

func (e *VossError) Error() string {
	return fmt.Sprintf("HTTP %d: %s", e.Status, e.Detail)
}

// checkResponse returns nil for 2xx (body left open for the caller), else a
// *VossError with status + `detail`. Tolerates an empty/bad body. Mirrors
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
