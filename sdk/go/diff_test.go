package voss

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"
)

func TestDiffReplyAndCancel(t *testing.T) {
	for _, choices := range [][]DiffReplyDecisions{{Accept, Skip}, {Reject}, nil} {
		for _, status := range []string{"ok", "stale"} {
			t.Run(fmt.Sprintf("%s/%d", status, len(choices)), func(t *testing.T) {
				srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
					if r.Method != "POST" || r.URL.EscapedPath() != "/session/session%2Fid/diff" {
						t.Errorf("unexpected request: %s %s", r.Method, r.URL)
					}
					var body DiffReply
					if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
						t.Error(err)
					}
					want := choices
					if want == nil {
						want = []DiffReplyDecisions{}
					}
					if body.Id != "proposal" || !reflect.DeepEqual(body.Decisions, want) {
						t.Errorf("incorrect reply: %+v", body)
					}
					_ = json.NewEncoder(w).Encode(map[string]string{"status": status})
				}))
				defer srv.Close()
				stale, err := AttachClient(srv.URL, "test").ReplyDiff(context.Background(), "session/id", "proposal", choices)
				if err != nil || stale != (status == "stale") {
					t.Fatalf("stale=%v, err=%v", stale, err)
				}
			})
		}
	}
}

func TestOpenSessionDiffReviewOptIn(t *testing.T) {
	for _, review := range []bool{false, true} {
		for _, resume := range []string{"", "saved"} {
			srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				var body map[string]any
				if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
					t.Error(err)
				}
				got, present := body["review_diffs"]
				if review && got != true || !review && present {
					t.Errorf("review opt-in: %v", body)
				}
				if resume != "" && body["resume"] != resume {
					t.Errorf("resume missing: %v", body)
				}
				w.WriteHeader(http.StatusCreated)
				_, _ = w.Write([]byte(`{"id":"s1"}`))
			}))
			_, err := AttachClient(srv.URL, "test").OpenSession(context.Background(), SessionOptions{ReviewDiffs: review, Resume: resume})
			srv.Close()
			if err != nil {
				t.Fatal(err)
			}
		}
	}
}
