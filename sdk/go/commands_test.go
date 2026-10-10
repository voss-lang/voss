package voss

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"
)

func TestCommandCatalogAndDispatch(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer test" {
			t.Error("missing bearer")
		}
		if r.Method == http.MethodGet && r.URL.Path == "/commands" {
			_, _ = w.Write([]byte(`{"v":1,"commands":[{"name":"/skills","description":"list skills"}]}`))
			return
		}
		if r.Method != http.MethodPost || r.URL.Path != "/session/sess-1/command" {
			t.Errorf("unexpected request: %s %s", r.Method, r.URL)
		}
		var body map[string]any
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			t.Error(err)
		}
		switch body["name"] {
		case "/skills":
			if _, ok := body["args"]; ok {
				t.Error("empty args should be omitted")
			}
			_, _ = w.Write([]byte(`{"v":1,"stdout":"review-fixture","stderr":""}`))
		case "/agents":
			if !reflect.DeepEqual(body["args"], []any{"extra argument"}) {
				t.Errorf("args = %v", body["args"])
			}
			_, _ = w.Write([]byte(`{"v":1,"stdout":"","stderr":"usage: /agents"}`))
		default:
			w.WriteHeader(http.StatusBadRequest)
			_, _ = w.Write([]byte(`{"detail":"Unknown command"}`))
		}
	}))
	defer srv.Close()
	client := AttachClient(srv.URL, "test")
	ctx := context.Background()
	catalog, err := client.ListCommands(ctx)
	if err != nil || len(catalog.Commands) != 1 || catalog.Commands[0].Name != "/skills" {
		t.Fatalf("catalog = %+v, %v", catalog, err)
	}
	result, err := client.ExecuteCommand(ctx, "sess-1", "/skills", nil)
	if err != nil || result.Stdout == nil || *result.Stdout != "review-fixture" {
		t.Fatalf("result = %+v, %v", result, err)
	}
	result, err = client.ExecuteCommand(ctx, "sess-1", "/agents", []string{"extra argument"})
	if err != nil || result.Stderr == nil || *result.Stderr != "usage: /agents" {
		t.Fatalf("usage = %+v, %v", result, err)
	}
	_, err = client.ExecuteCommand(ctx, "sess-1", "/unknown", nil)
	var ve *VossError
	if !errors.As(err, &ve) || ve.Status != http.StatusBadRequest || ve.Detail != "Unknown command" {
		t.Fatalf("command error = %v", err)
	}
}
