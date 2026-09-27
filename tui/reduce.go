package main

import (
	"fmt"
	"strings"

	voss "github.com/vosslang/voss/sdk/go"
)

type blockKind int

const (
	blockUser blockKind = iota
	blockAssistant
	blockPlan
	blockTool
	blockClarify
	blockWarning
	blockError
	blockNotice
	blockToolArgs
)

// block is a finished piece of transcript, printed to scrollback once.
type block struct {
	kind blockKind
	text string
}

// turn is the session state that server events change.
type turn struct {
	busy          bool
	streaming     string
	thinking      string
	permission    *voss.PermissionUpdated
	lastTool      *voss.ToolEvent
	pendingTool   string
	streamedChars int
	model         string
	tokens        int
	costUSD       float64
	ctxPct        float64
}

// reduce applies one server event and returns the blocks to commit to scrollback.
func reduce(t turn, ev voss.TypedEvent) (turn, []block) {
	switch e := ev.(type) {
	case voss.UserEvent:
		t.busy = true
		t.streamedChars = 0
		return t, []block{{blockUser, e.Task}}
	case voss.ThinkingEvent:
		t.thinking = e.Label
	case voss.PlanEvent:
		if e.Steps == nil || len(*e.Steps) == 0 {
			return t, nil
		}
		names := make([]string, len(*e.Steps))
		for i, s := range *e.Steps {
			names[i] = s.Name
			if s.Args != nil {
				if path, ok := (*s.Args)["path"].(string); ok && path != "" {
					names[i] += " " + path
				}
			}
		}
		return t, []block{{blockPlan, "plan: " + strings.Join(names, " → ")}}
	case voss.ToolEvent:
		if e.State == "pending" {
			t.pendingTool = e.Name
			return t, nil
		}
		t.pendingTool = ""
		t.lastTool = &e
		text := e.Name + " " + toolGlyph(e.State)
		if e.Summary != nil {
			if line, _, _ := strings.Cut(strings.TrimSpace(*e.Summary), "\n"); line != "" {
				text += " " + line
			}
		}
		return t, []block{{blockTool, text}}
	case voss.StreamDelta:
		t.streaming += e.Text
		t.streamedChars += len(e.Text)
	case voss.StreamFinalize:
		kind := blockAssistant
		if e.Role == "system" {
			kind = blockError
		}
		return flush(t, kind)
	case voss.FinalEvent:
		var out []block
		t, out = flush(t, blockAssistant)
		if e.Text != "" {
			out = append(out, block{blockAssistant, e.Text})
		}
		return t, out
	case voss.ClarifyEvent:
		return t, []block{{blockClarify, e.Question}}
	case voss.WarningEvent:
		return t, []block{{blockWarning, e.Message}}
	case voss.CognitionOverflow:
		return t, []block{{blockWarning, overBudget("architecture context", e.ArchitectureTokens, e.Budget)}}
	case voss.PrinciplesOverflow:
		return t, []block{{blockWarning, overBudget("principles", e.PrinciplesTokens, e.Budget)}}
	case voss.InstructionsOverflow:
		msg := overBudget("instructions", e.InstructionsTokens, e.Budget)
		if e.Truncated != nil && len(*e.Truncated) > 0 {
			msg += "; truncated " + strings.Join(*e.Truncated, ", ")
		}
		return t, []block{{blockWarning, msg}}
	case voss.StatusEvent:
		if e.Model != "" {
			t.model = e.Model
		}
		t.tokens = e.Tokens
		t.costUSD = float64(e.CostUsd)
		t.ctxPct = float64(e.CtxPct)
	case voss.PermissionUpdated:
		t.permission = &e
	case voss.SessionIdle:
		var out []block
		t, out = flush(t, blockAssistant)
		t.busy = false
		t.thinking = ""
		t.pendingTool = ""
		t.permission = nil
		return t, out
	case voss.UnknownEvent:
		return t, []block{{blockNotice, fmt.Sprintf("unsupported event %q from a newer server", e.Type)}}
	}
	return t, nil
}

// flush commits streamed text that has not been committed yet.
func flush(t turn, kind blockKind) (turn, []block) {
	if strings.TrimSpace(t.streaming) == "" {
		t.streaming = ""
		return t, nil
	}
	b := block{kind, strings.Trim(t.streaming, "\n")}
	t.streaming = ""
	return t, []block{b}
}

func overBudget(what string, tokens int, budget *int) string {
	if budget == nil {
		return fmt.Sprintf("%s is %d tokens, over budget", what, tokens)
	}
	return fmt.Sprintf("%s is %d tokens, over the %d-token budget", what, tokens, *budget)
}

func toolGlyph(state string) string {
	switch state {
	case "ok":
		return "✓"
	case "error":
		return "✗"
	}
	return state
}
