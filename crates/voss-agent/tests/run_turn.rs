//! run_turn end-to-end behavior + D-08 status invariants.

use std::sync::Arc;

use async_trait::async_trait;
use voss_agent::{run_turn, AlwaysAllow, EpisodicMemory, Plan, TurnConfig};
use voss_providers::{CompleteRequest, ModelProvider, ProviderResponse};
use voss_render::NdjsonRender;
use voss_tools::Tool;

struct CannedProvider {
    plan: Plan,
}

#[async_trait]
impl ModelProvider for CannedProvider {
    async fn complete(&mut self, req: CompleteRequest) -> anyhow::Result<ProviderResponse> {
        assert_eq!(req.max_tokens, Some(4096));
        let plan_json = serde_json::to_value(&self.plan)?;
        Ok(ProviderResponse {
            text: plan_json.to_string(),
            model: "claude-sonnet-4-5".into(),
            prompt_tokens: 100,
            completion_tokens: 50,
            cost_usd: 0.01,
            raw: plan_json.clone(),
            parsed: Some(plan_json),
        })
    }
}

#[tokio::test]
async fn high_confidence_plan_executes_steps() {
    let tmp = tempfile::tempdir().unwrap();
    std::fs::write(tmp.path().join("a.txt"), "hello").unwrap();
    let tools: Vec<Arc<dyn Tool>> = voss_tools::default_toolset(tmp.path());

    let plan = Plan {
        rationale: "list files".into(),
        steps: vec![voss_agent::ToolCall {
            name: "fs_glob".into(),
            args: serde_json::Map::from_iter([("pattern".to_string(), serde_json::json!("*.txt"))]),
            why: "see files".into(),
        }],
        confidence: 0.9,
        open_question: None,
        final_when_done: "Result: {{step_0}}".into(),
    };
    let mut provider = CannedProvider { plan: plan.clone() };
    let mut renderer = NdjsonRender {
        out: Vec::<u8>::new(),
    };
    let mut perms = AlwaysAllow;
    let mut history = EpisodicMemory::new(40);

    let result = run_turn(
        "list txt files",
        &tools,
        tmp.path(),
        &mut renderer,
        &mut provider,
        Some(&mut history),
        &mut perms,
        TurnConfig::default(),
        false,
    )
    .await
    .unwrap();

    assert_eq!(result.confidence, 0.9);
    assert!(
        result.final_text.contains("a.txt"),
        "expected a.txt in {:?}",
        result.final_text
    );
    assert_eq!(history.last(2).len(), 2);
}

#[tokio::test]
async fn low_confidence_emits_clarify() {
    let tmp = tempfile::tempdir().unwrap();
    let tools: Vec<Arc<dyn Tool>> = voss_tools::default_toolset(tmp.path());
    let plan = Plan {
        rationale: "unsure".into(),
        steps: vec![],
        confidence: 0.3,
        open_question: Some("which file?".into()),
        final_when_done: "".into(),
    };
    let mut provider = CannedProvider { plan: plan.clone() };
    let mut renderer = NdjsonRender {
        out: Vec::<u8>::new(),
    };
    let mut perms = AlwaysAllow;
    let result = run_turn(
        "vague task",
        &tools,
        tmp.path(),
        &mut renderer,
        &mut provider,
        None,
        &mut perms,
        TurnConfig::default(),
        true,
    )
    .await
    .unwrap();
    assert_eq!(result.tool_results.len(), 0);
    assert_eq!(result.final_text, "which file?");
}

#[tokio::test]
async fn json_mode_suppresses_status() {
    let tmp = tempfile::tempdir().unwrap();
    let tools: Vec<Arc<dyn Tool>> = voss_tools::default_toolset(tmp.path());
    let plan = Plan {
        rationale: "".into(),
        steps: vec![],
        confidence: 1.0,
        open_question: None,
        final_when_done: "done".into(),
    };
    let mut provider = CannedProvider { plan };
    let mut renderer = NdjsonRender {
        out: Vec::<u8>::new(),
    };
    let mut perms = AlwaysAllow;
    let _ = run_turn(
        "task",
        &tools,
        tmp.path(),
        &mut renderer,
        &mut provider,
        None,
        &mut perms,
        TurnConfig::default(),
        true, // suppress_status = true → --json mode
    )
    .await
    .unwrap();
    let s = String::from_utf8(renderer.out).unwrap();
    assert!(
        !s.contains("\"type\":\"status\""),
        "status emitted in --json: {s}"
    );
}

#[tokio::test]
async fn tty_mode_emits_status_once() {
    let tmp = tempfile::tempdir().unwrap();
    let tools: Vec<Arc<dyn Tool>> = voss_tools::default_toolset(tmp.path());
    let plan = Plan {
        rationale: "".into(),
        steps: vec![],
        confidence: 1.0,
        open_question: None,
        final_when_done: "done".into(),
    };
    let mut provider = CannedProvider { plan };
    let mut renderer = NdjsonRender {
        out: Vec::<u8>::new(),
    };
    let mut perms = AlwaysAllow;
    let _ = run_turn(
        "task",
        &tools,
        tmp.path(),
        &mut renderer,
        &mut provider,
        None,
        &mut perms,
        TurnConfig::default(),
        false, // suppress_status = false → TTY mode
    )
    .await
    .unwrap();
    let s = String::from_utf8(renderer.out).unwrap();
    let count = s.matches("\"type\":\"status\"").count();
    assert_eq!(
        count, 1,
        "expected exactly 1 status event in TTY mode, got {count} in: {s}"
    );
}
