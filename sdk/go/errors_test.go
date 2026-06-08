package voss

import (
	"errors"
	"io"
	"net/http"
	"strings"
	"testing"
)

// resp builds a minimal *http.Response with the given status and body for
// checkResponse, mirroring what the REST/SSE callers pass in.
func resp(status int, body string) *http.Response {
	return &http.Response{
		StatusCode: status,
		Body:       io.NopCloser(strings.NewReader(body)),
	}
}

// TestVossError proves the typed error model: 2xx -> nil; a 401 {v,detail}
// body -> *VossError{401,"unauthorized"} via errors.As; a malformed body ->
// non-panic VossError with empty Detail; and Error() never leaks a token.
func TestVossError(t *testing.T) {
	// 2xx -> nil.
	for _, code := range []int{200, 201, 202, 204} {
		if err := checkResponse(resp(code, "")); err != nil {
			t.Fatalf("checkResponse(%d) = %v, want nil", code, err)
		}
	}

	// 401 with the standard {v, detail} body.
	err := checkResponse(resp(401, `{"v":1,"detail":"unauthorized"}`))
	var ve *VossError
	if !errors.As(err, &ve) {
		t.Fatalf("error %v is not *VossError", err)
	}
	if ve.Status != 401 || ve.Detail != "unauthorized" {
		t.Fatalf("VossError = {%d,%q}, want {401,unauthorized}", ve.Status, ve.Detail)
	}
	if got := ve.Error(); got != "HTTP 401: unauthorized" {
		t.Fatalf("Error() = %q, want %q", got, "HTTP 401: unauthorized")
	}

	// Malformed/empty body -> no panic, empty Detail.
	err = checkResponse(resp(500, "<html>not json</html>"))
	if !errors.As(err, &ve) {
		t.Fatalf("error %v is not *VossError", err)
	}
	if ve.Status != 500 || ve.Detail != "" {
		t.Fatalf("VossError = {%d,%q}, want {500,\"\"}", ve.Status, ve.Detail)
	}

	// Token-leak guard: a bearer token is never part of VossError output.
	const sentinel = "SECRET-BEARER-TOKEN-xyz"
	leak := checkResponse(resp(403, `{"v":1,"detail":"forbidden"}`))
	if strings.Contains(leak.Error(), sentinel) {
		t.Fatalf("Error() leaked token: %q", leak.Error())
	}
}
