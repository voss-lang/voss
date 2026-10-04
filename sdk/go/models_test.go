package voss

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestModelCatalogAndSelection(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer test" {
			t.Error("missing bearer")
		}
		if r.Method == http.MethodGet && r.URL.Path == "/models" {
			_, _ = w.Write([]byte(`{"models":[{"id":"gpt-6.1-sol","name":"GPT 6.1 Sol","auth":"codex","provider":"openai","provider_label":"Codex subscription","connected":true,"recommended":false}],"warning":""}`))
			return
		}
		if r.Method != http.MethodPost || r.URL.Path != "/session/sess-1/model" {
			t.Errorf("unexpected request: %s %s", r.Method, r.URL)
		}
		var selection ModelSelection
		if err := json.NewDecoder(r.Body).Decode(&selection); err != nil {
			t.Error(err)
		}
		if selection.Model == "missing" {
			w.WriteHeader(http.StatusBadRequest)
			_, _ = w.Write([]byte(`{"detail":"No matching model"}`))
			return
		}
		if selection != (ModelSelection{Model: "gpt-6.1-sol", Auth: "codex", Provider: "openai"}) {
			t.Errorf("selection = %+v", selection)
		}
		_, _ = w.Write([]byte(`{"id":"sess-1","model":"gpt-6.1-sol","provider":"Codex","auth":"codex-oauth"}`))
	}))
	defer srv.Close()
	client := AttachClient(srv.URL, "test")
	catalog, err := client.ListModels(context.Background())
	if err != nil || len(catalog.Models) != 1 || !catalog.Models[0].Connected || catalog.Models[0].Auth != "codex" {
		t.Fatalf("catalog = %+v, %v", catalog, err)
	}
	info, err := client.SelectModel(context.Background(), "sess-1", ModelSelection{Model: "gpt-6.1-sol", Auth: "codex", Provider: "openai"})
	if err != nil || info.Model != "gpt-6.1-sol" || info.Provider != "Codex" || info.Auth != "codex-oauth" {
		t.Fatalf("selection = %+v, %v", info, err)
	}
	_, err = client.SelectModel(context.Background(), "sess-1", ModelSelection{Model: "missing"})
	var ve *VossError
	if !errors.As(err, &ve) || ve.Status != http.StatusBadRequest {
		t.Fatalf("selection error = %v", err)
	}
}
