package voss

import "fmt"

// TypedEvent is the sealed interface implemented by all 21 AgentEvent structs.
// Hand-written: oapi-codegen emits the structs but no Go sum type or dispatcher.
type TypedEvent interface{ eventType() string }

// eventType binds each generated struct to its discriminator (value receivers).
func (ServerConnected) eventType() string    { return "server.connected" }
func (SessionIdle) eventType() string        { return "session.idle" }
func (PermissionUpdated) eventType() string  { return "permission.updated" }
func (BannerEvent) eventType() string        { return "banner" }
func (UserEvent) eventType() string          { return "user" }
func (ThinkingEvent) eventType() string      { return "thinking" }
func (PlanEvent) eventType() string          { return "plan" }
func (ToolEvent) eventType() string          { return "tool" }
func (ClarifyEvent) eventType() string       { return "clarify" }
func (FinalEvent) eventType() string         { return "final" }
func (StreamDelta) eventType() string        { return "stream.delta" }
func (StreamFinalize) eventType() string     { return "stream.finalize" }
func (StatusEvent) eventType() string        { return "status" }
func (CognitionLoaded) eventType() string    { return "cognition_loaded" }
func (CognitionOverflow) eventType() string  { return "cognition_overflow" }
func (PrinciplesOverflow) eventType() string { return "principles_overflow" }
func (WarningEvent) eventType() string       { return "warning" }
func (ProbableEvent) eventType() string      { return "probable" }
func (BudgetUpdated) eventType() string      { return "budget.updated" }
func (ConfidenceUpdated) eventType() string  { return "confidence.updated" }
func (GateUpdated) eventType() string        { return "gate.updated" }

// ErrUnknownEventType is returned by Decode for any `type` outside the 21-member
// set, carrying the raw type string. Match via errors.As.
type ErrUnknownEventType struct{ Type string }

func (e ErrUnknownEventType) Error() string { return "unknown event type: " + e.Type }

// Decode dispatches an EventEnvelope to its typed value via the discriminator.
// An unknown `type` returns (nil, ErrUnknownEventType{...}) — no silent drop.
func Decode(env EventEnvelope) (TypedEvent, error) {
	disc, err := env.Event.Discriminator()
	if err != nil {
		return nil, fmt.Errorf("event discriminator: %w", err)
	}
	switch disc {
	case "server.connected":
		v, err := env.Event.AsServerConnected()
		return v, err
	case "session.idle":
		v, err := env.Event.AsSessionIdle()
		return v, err
	case "permission.updated":
		v, err := env.Event.AsPermissionUpdated()
		return v, err
	case "banner":
		v, err := env.Event.AsBannerEvent()
		return v, err
	case "user":
		v, err := env.Event.AsUserEvent()
		return v, err
	case "thinking":
		v, err := env.Event.AsThinkingEvent()
		return v, err
	case "plan":
		v, err := env.Event.AsPlanEvent()
		return v, err
	case "tool":
		v, err := env.Event.AsToolEvent()
		return v, err
	case "clarify":
		v, err := env.Event.AsClarifyEvent()
		return v, err
	case "final":
		v, err := env.Event.AsFinalEvent()
		return v, err
	case "stream.delta":
		v, err := env.Event.AsStreamDelta()
		return v, err
	case "stream.finalize":
		v, err := env.Event.AsStreamFinalize()
		return v, err
	case "status":
		v, err := env.Event.AsStatusEvent()
		return v, err
	case "cognition_loaded":
		v, err := env.Event.AsCognitionLoaded()
		return v, err
	case "cognition_overflow":
		v, err := env.Event.AsCognitionOverflow()
		return v, err
	case "principles_overflow":
		v, err := env.Event.AsPrinciplesOverflow()
		return v, err
	case "warning":
		v, err := env.Event.AsWarningEvent()
		return v, err
	case "probable":
		v, err := env.Event.AsProbableEvent()
		return v, err
	case "budget.updated":
		v, err := env.Event.AsBudgetUpdated()
		return v, err
	case "confidence.updated":
		v, err := env.Event.AsConfidenceUpdated()
		return v, err
	case "gate.updated":
		v, err := env.Event.AsGateUpdated()
		return v, err
	default:
		return nil, ErrUnknownEventType{Type: disc}
	}
}
