//! Protocol event parsing (H2.4).
//!
//! Maps an SSE frame (`event:` name + JSON `data`) to a UI-facing [`AppEvent`].
//! Mirrors `.planning/PROTOCOL.md` §6 / the server's `events.py`. Unknown event
//! names degrade to [`AppEvent::Other`] (forward-compatible), and missing/odd
//! fields default rather than erroring — a thin client must never crash on a
//! server it is slightly out of sync with.

/// UI-facing event decoded from the wire.
#[derive(Debug, Clone, PartialEq)]
pub enum AppEvent {
    Connected,
    User(String),
    Thinking(String),
    Plan { confidence: f64, steps: Vec<String> },
    Tool { name: String, state: String },
    StreamDelta(String),
    StreamFinalize,
    Final { text: String, confidence: f64 },
    Clarify { question: String, confidence: f64 },
    Status { tokens: u64, cost_usd: f64 },
    Permission { id: String, tool_name: String },
    Warning(String),
    SessionIdle,
    Error(String),
    /// An event type this client does not specifically render.
    Other(String),
}

impl AppEvent {
    /// Decode an SSE frame into an [`AppEvent`]. Never panics.
    pub fn from_wire(event: &str, data: &str) -> AppEvent {
        let v: serde_json::Value = serde_json::from_str(data).unwrap_or(serde_json::Value::Null);
        let s = |k: &str| {
            v.get(k)
                .and_then(serde_json::Value::as_str)
                .unwrap_or("")
                .to_string()
        };
        let f = |k: &str| v.get(k).and_then(serde_json::Value::as_f64).unwrap_or(0.0);
        match event {
            "server.connected" => AppEvent::Connected,
            "user" => AppEvent::User(s("task")),
            "thinking" => AppEvent::Thinking(s("label")),
            "plan" => AppEvent::Plan {
                confidence: f("confidence"),
                steps: v
                    .get("steps")
                    .and_then(serde_json::Value::as_array)
                    .map(|a| {
                        a.iter()
                            .filter_map(|st| {
                                st.get("name").and_then(serde_json::Value::as_str).map(String::from)
                            })
                            .collect()
                    })
                    .unwrap_or_default(),
            },
            "tool" => AppEvent::Tool {
                name: s("name"),
                state: s("state"),
            },
            "stream.delta" => AppEvent::StreamDelta(s("text")),
            "stream.finalize" => AppEvent::StreamFinalize,
            "final" => AppEvent::Final {
                text: s("text"),
                confidence: f("confidence"),
            },
            "clarify" => AppEvent::Clarify {
                question: s("question"),
                confidence: f("confidence"),
            },
            "status" => AppEvent::Status {
                tokens: v.get("tokens").and_then(serde_json::Value::as_u64).unwrap_or(0),
                cost_usd: f("cost_usd"),
            },
            "permission.updated" => AppEvent::Permission {
                id: s("id"),
                tool_name: s("tool_name"),
            },
            "warning" => AppEvent::Warning(s("message")),
            "session.idle" => AppEvent::SessionIdle,
            other => AppEvent::Other(other.to_string()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_known_events() {
        assert_eq!(
            AppEvent::from_wire("stream.delta", r#"{"v":1,"text":"hi"}"#),
            AppEvent::StreamDelta("hi".into())
        );
        assert_eq!(
            AppEvent::from_wire("session.idle", r#"{"v":1,"session_id":"s"}"#),
            AppEvent::SessionIdle
        );
        match AppEvent::from_wire("plan", r#"{"confidence":0.9,"steps":[{"name":"fs_read"}]}"#) {
            AppEvent::Plan { confidence, steps } => {
                assert!((confidence - 0.9).abs() < 1e-9);
                assert_eq!(steps, vec!["fs_read".to_string()]);
            }
            other => panic!("expected Plan, got {other:?}"),
        }
    }

    #[test]
    fn unknown_event_is_other() {
        assert_eq!(
            AppEvent::from_wire("budget.updated", "{}"),
            AppEvent::Other("budget.updated".into())
        );
    }

    #[test]
    fn malformed_data_does_not_panic() {
        assert_eq!(
            AppEvent::from_wire("stream.delta", "not json"),
            AppEvent::StreamDelta(String::new())
        );
    }
}
