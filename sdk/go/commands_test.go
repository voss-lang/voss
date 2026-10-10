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
		case "/btrace":
			_, _ = w.Write([]byte(`{"stdout":"No recorded budget timeline.","inspection":{"title":"Budget trace","text":"No recorded budget timeline."}}`))
		case "/symbol":
			_, _ = w.Write([]byte(`{"stdout":"app.py:1","code":{"query":"/symbol sample_entry","items":[{"file":"app.py","line":1,"name":"sample_entry","language":"python","source":"index","snippet":"def sample_entry(): pass"}],"truncated":false}}`))
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
	result, err = client.ExecuteCommand(ctx, "sess-1", "/symbol", []string{"sample_entry"})
	if err != nil || result.Code == nil || len(result.Code.Items) != 1 || result.Code.Items[0].Line != 1 || result.Code.Items[0].Snippet != "def sample_entry(): pass" {
		t.Fatalf("code results = %+v, %v", result, err)
	}
	result, err = client.ExecuteCommand(ctx, "sess-1", "/btrace", nil)
	if err != nil || result.Inspection == nil || result.Inspection.Title != "Budget trace" || result.Inspection.Text != "No recorded budget timeline." {
		t.Fatalf("inspection = %+v, %v", result, err)
	}
}
