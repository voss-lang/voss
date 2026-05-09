use std::path::PathBuf;

use voss_agent::{Plan, ToolCall};
use voss_render::{NdjsonRender, Render, ToolState};

fn capture<F: FnOnce(&mut NdjsonRender<Vec<u8>>)>(f: F) -> String {
    let mut r = NdjsonRender { out: Vec::new() };
    f(&mut r);
    String::from_utf8(r.out).unwrap()
}

#[test]
fn ndjson_banner() {
    insta::assert_snapshot!(capture(|r| r.banner(
        "claude-sonnet-4-5",
        &PathBuf::from("/tmp/x"),
        "clean"
    )));
}

#[test]
fn ndjson_user() {
    insta::assert_snapshot!(capture(|r| r.show_user("hello")));
}

#[test]
fn ndjson_thinking() {
    insta::assert_snapshot!(capture(|r| r.show_thinking("planning")));
}

#[test]
fn ndjson_plan() {
    let plan = Plan {
        rationale: "r".into(),
        steps: vec![ToolCall {
            name: "fs_read".into(),
            args: Default::default(),
            why: "".into(),
        }],
        confidence: 0.9,
        open_question: None,
        final_when_done: "done".into(),
    };
    insta::assert_snapshot!(capture(|r| r.show_plan(&plan, 0.0)));
}

#[test]
fn ndjson_tool() {
    insta::assert_snapshot!(capture(|r| r.show_tool_call(
        "fs_read",
        &serde_json::json!({"path": "a.txt"}),
        "ok",
        ToolState::Ok
    )));
}

#[test]
fn ndjson_clarify() {
    insta::assert_snapshot!(capture(|r| r.show_clarify("what?", 0.4)));
}

#[test]
fn ndjson_final() {
    insta::assert_snapshot!(capture(|r| r.show_final("done", 0.9, 0.01)));
}

#[test]
fn ndjson_status() {
    insta::assert_snapshot!(capture(|r| r.status("claude-sonnet-4-5", 1234, 0.05, 0.4)));
}

/// Versioned envelope: every event payload contains `"v": 1`.
#[test]
fn every_event_has_v_field() {
    let s = capture(|r| {
        r.banner("m", &PathBuf::from("/x"), "ok");
        r.show_user("hi");
        r.show_thinking("p");
        let plan = Plan {
            rationale: "".into(),
            steps: vec![],
            confidence: 1.0,
            open_question: None,
            final_when_done: "".into(),
        };
        r.show_plan(&plan, 0.0);
        r.show_tool_call("fs_read", &serde_json::json!({}), "ok", ToolState::Ok);
        r.show_clarify("q", 0.4);
        r.show_final("a", 0.9, 0.0);
        r.status("m", 0, 0.0, 0.0);
    });
    let lines: Vec<&str> = s.lines().collect();
    assert_eq!(lines.len(), 8, "expected 8 events, got {}", lines.len());
    for line in lines {
        let v: serde_json::Value =
            serde_json::from_str(line).unwrap_or_else(|e| panic!("bad json: {line}: {e}"));
        assert_eq!(v["v"], 1, "missing/wrong v in: {line}");
    }
}
