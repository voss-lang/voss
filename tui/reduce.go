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
	blockRole
	blockConfidence
	blockTool
	blockToolArgs
)

// block is one finished piece of transcript, mirroring the Textual widgets:
// UserBlock, AssistantBlock, RoleBlock, ConfidenceBar and tool rows.
type block struct {
	kind   blockKind
	text   string
	role   string  // RoleBlock label
	footer string  // AssistantBlock metadata line, set when a stream finalizes
	conf   float64 // ConfidenceBar value
	joined bool    // no blank line before it, like Textual's separate=False
}

func userBlock(text string) block      { return block{kind: blockUser, text: text} }
func assistantBlock(text string) block { return block{kind: blockAssistant, text: text} }
func roleBlock(role, text string) block {
	return block{kind: blockRole, role: role, text: text}
}

// turn is the session state that server events change.
type turn struct {
	busy          bool
	streaming     string
	interrupted   bool
	thinking      string // the persistent toast; Textual clears it on final, not idle
	permission    *voss.PermissionUpdated
	lastTool      *voss.ToolEvent
	pendingTool   string
	streamedChars int
	model         string
	tokens        int
	costUSD       float64
	ctxPct        float64
}

// reduce applies one server event and returns the blocks to commit. Block
// text follows voss/harness/tui/renderer.py.
func reduce(t turn, ev voss.TypedEvent) (turn, []block) {
	switch e := ev.(type) {
	case voss.UserEvent:
		t.busy = true
		t.streamedChars = 0
		return t, []block{userBlock(e.Task)}
	case voss.ThinkingEvent:
		t.thinking = e.Label
	case voss.PlanEvent:
		var lines []string
		if e.Steps != nil {
			for _, s := range *e.Steps {
				lines = append(lines, "  · "+s.Name)
			}
		}
		body := strings.Join(lines, "\n")
		if body == "" {
			body = "(empty plan)"
		}
		return t, []block{roleBlock("plan", body)}
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
		return t, []block{{kind: blockTool, text: text, joined: true}}
	case voss.StreamDelta:
		t.streaming += e.Text
		t.streamedChars += len(e.Text)
	case voss.StreamFinalize:
		footer := e.Role
		if e.Timestamp != nil && *e.Timestamp != "" {
			footer += " · " + *e.Timestamp
		}
		if e.CostUsd != nil {
			footer += fmt.Sprintf(" · $%.4f", *e.CostUsd)
		}
		if e.Confidence != nil {
			footer += fmt.Sprintf(" · conf %.2f", *e.Confidence)
		}
		if t.interrupted {
			footer += " · interrupted"
		}
		t.interrupted = false
		t.thinking = ""
		return flush(t, footer)
	case voss.FinalEvent:
		var out []block
		t.thinking = ""
		t, out = flush(t, "")
		return t, append(out, assistantBlock(e.Text))
	case voss.ClarifyEvent:
		return t, []block{roleBlock("clarify", e.Question), {kind: blockConfidence, conf: float64(e.Confidence), joined: true}}
	case voss.WarningEvent:
		return t, []block{roleBlock("warning", glyphs.Warn+" "+e.Message)}
	case voss.CognitionLoaded:
		body := fmt.Sprintf("cognition: architecture (%.1fk) + %d constraints", float64(e.ArchitectureTokens)/1000, e.ConstraintsCount)
		plans, decisions := deref(e.PlansLoaded), deref(e.DecisionsLoaded)
		if plans > 0 || decisions > 0 {
			body += fmt.Sprintf(" + %d plans + %d decisions", plans, decisions)
		}
		return t, []block{roleBlock("cognition", body)}
	case voss.CognitionOverflow:
		return t, []block{roleBlock("warning", fmt.Sprintf(
			"%s architecture.md is %d tokens (over %d budget) — /analyze can rewrite a tighter digest",
			glyphs.Warn, e.ArchitectureTokens, derefOr(e.Budget, 6000)))}
	case voss.PrinciplesOverflow:
		return t, []block{roleBlock("warning", fmt.Sprintf(
			"%s principles block is %d tokens (over %d budget) — truncated",
			glyphs.Warn, e.PrinciplesTokens, derefOr(e.Budget, 1000)))}
	case voss.InstructionsOverflow:
		var truncated []string
		if e.Truncated != nil {
			truncated = *e.Truncated
		}
		return t, []block{roleBlock("warning", fmt.Sprintf(
			"%s instruction files truncated to %d tokens (%s)",
			glyphs.Warn, derefOr(e.Budget, 4000), strings.Join(truncated, ", ")))}
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
		t, out = flush(t, "")
		t.busy = false
		t.pendingTool = ""
		t.permission = nil
		t.interrupted = false
		return t, out
	case voss.UnknownEvent:
		return t, []block{roleBlock("notice", fmt.Sprintf("unsupported event %q from a newer server", e.Type))}
	}
	return t, nil
}

// flush commits streamed text as an assistant block joined to what precedes
// it, like Textual's streaming AssistantBlock.
func flush(t turn, footer string) (turn, []block) {
	text := t.streaming
	t.streaming = ""
	if strings.TrimSpace(text) == "" {
		return t, nil
	}
	return t, []block{{kind: blockAssistant, text: text, footer: footer, joined: true}}
}

func deref(p *int) int { return derefOr(p, 0) }

func derefOr(p *int, fallback int) int {
	if p == nil {
		return fallback
	}
	return *p
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
