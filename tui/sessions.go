package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"

	voss "github.com/vosslang/voss/sdk/go"
)

// savedRecord is the part of a `.voss/sessions/*.json` file the listing needs.
type savedRecord struct {
	Id           string            `json:"id"`
	Name         string            `json:"name"`
	Cwd          string            `json:"cwd"`
	Model        string            `json:"model"`
	UpdatedAt    string            `json:"updated_at"`
	TotalCostUsd float64           `json:"total_cost_usd"`
	Turns        []json.RawMessage `json:"turns"`
}

// readSavedSessions reads the session files the Python harness writes under
// cwd, newest first, skipping files that do not parse. No server needed.
func readSavedSessions(cwd string) []voss.SavedSession {
	paths, _ := filepath.Glob(filepath.Join(cwd, ".voss", "sessions", "*.json"))
	var out []voss.SavedSession
	for _, p := range paths {
		raw, err := os.ReadFile(p)
		if err != nil {
			continue
		}
		var r savedRecord
		if err := json.Unmarshal(raw, &r); err != nil || r.Id == "" {
			continue
		}
		out = append(out, voss.SavedSession{
			Id:           r.Id,
			Name:         r.Name,
			Cwd:          r.Cwd,
			Model:        r.Model,
			UpdatedAt:    r.UpdatedAt,
			TotalCostUsd: r.TotalCostUsd,
			Turns:        len(r.Turns),
		})
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].UpdatedAt > out[j].UpdatedAt })
	return out
}

func printSessions(w io.Writer, cwd string, sessions []voss.SavedSession) {
	if len(sessions) == 0 {
		fmt.Fprintf(w, "no saved sessions for %s\n", cwd)
		return
	}
	fmt.Fprintf(w, "%-14s %-24s %5s %9s  UPDATED\n", "ID", "NAME", "TURNS", "COST$")
	for _, s := range sessions {
		fmt.Fprintf(w, "%-14s %-24s %5d %9.4f  %s\n", s.Id, s.Name, s.Turns, s.TotalCostUsd, s.UpdatedAt)
	}
}
