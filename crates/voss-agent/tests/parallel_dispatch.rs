//! D-11..D-14 dispatch invariants.

use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use async_trait::async_trait;
use serde_json::{json, Value};

use voss_agent::{run_turn, AlwaysAllow, Plan, PermissionCheck, ToolCall, TurnConfig};
use voss_providers::{CompleteRequest, ModelProvider, ProviderResponse};
use voss_render::NdjsonRender;
use voss_tools::Tool;

/// Records (start_instant, end_instant) for each invocation.
#[derive(Default)]
struct Recorder {
    spans: Mutex<Vec<(String, Instant, Instant)>>,
    /// Concurrency tracking: counter increments on enter, decrements on exit;
    /// `peak` is the highest value the counter ever reaches.
    in_flight: AtomicUsize,
    peak: AtomicUsize,
}

impl Recorder {
    fn snapshot(&self) -> Vec<(String, Instant, Instant)> {
        self.spans.lock().unwrap().clone()
    }
}

struct ReadOnlyTool {
    label: &'static str,
    sleep_ms: u64,
    rec: Arc<Recorder>,
}

#[async_trait]
impl Tool for ReadOnlyTool {
    fn name(&self) -> &str {
        self.label
    }
    fn description(&self) -> &str {
        "test read-only"
    }
    fn schema(&self) -> Value {
        json!({"type": "object", "properties": {}, "required": []})
    }
    fn is_mutating(&self) -> bool {
        false
    }
    async fn invoke(&self, _args: Value) -> anyhow::Result<String> {
        let start = Instant::now();
        let now_in = self.rec.in_flight.fetch_add(1, Ordering::SeqCst) + 1;
        // Atomically push peak to max.
        let mut prev = self.rec.peak.load(Ordering::SeqCst);
        while now_in > prev {
            match self
                .rec
                .peak
                .compare_exchange(prev, now_in, Ordering::SeqCst, Ordering::SeqCst)
            {
                Ok(_) => break,
                Err(p) => prev = p,
            }
        }
        tokio::time::sleep(Duration::from_millis(self.sleep_ms)).await;
        self.rec.in_flight.fetch_sub(1, Ordering::SeqCst);
        let end = Instant::now();
        self.rec
            .spans
            .lock()
            .unwrap()
            .push((self.label.to_string(), start, end));
        Ok(format!("ro-{}", self.label))
    }
}

struct MutatingTool {
    label: &'static str,
    sleep_ms: u64,
    rec: Arc<Recorder>,
}

#[async_trait]
impl Tool for MutatingTool {
    fn name(&self) -> &str {
        self.label
    }
    fn description(&self) -> &str {
        "test mutating"
    }
    fn schema(&self) -> Value {
        json!({"type": "object", "properties": {}, "required": []})
    }
    fn is_mutating(&self) -> bool {
        true
    }
    async fn invoke(&self, _args: Value) -> anyhow::Result<String> {
        let start = Instant::now();
        tokio::time::sleep(Duration::from_millis(self.sleep_ms)).await;
        let end = Instant::now();
        self.rec
            .spans
            .lock()
            .unwrap()
            .push((self.label.to_string(), start, end));
        Ok(format!("mut-{}", self.label))
    }
}

/// Provider that returns a canned Plan.
struct CannedProvider {
    plan: Plan,
}

#[async_trait]
impl ModelProvider for CannedProvider {
    async fn complete(&mut self, _req: CompleteRequest) -> anyhow::Result<ProviderResponse> {
        let plan_json = serde_json::to_value(&self.plan)?;
        Ok(ProviderResponse {
            text: plan_json.to_string(),
            model: "test".into(),
            prompt_tokens: 1,
            completion_tokens: 1,
            cost_usd: 0.0,
            raw: plan_json.clone(),
            parsed: Some(plan_json),
        })
    }
}

fn step(name: &str) -> ToolCall {
    ToolCall {
        name: name.into(),
        args: Default::default(),
        why: "".into(),
    }
}

fn build_plan(steps: Vec<ToolCall>) -> Plan {
    Plan {
        rationale: "test".into(),
        steps,
        confidence: 0.99,
        open_question: None,
        final_when_done: "done".into(),
    }
}

fn cwd() -> PathBuf {
    std::env::temp_dir()
}

#[tokio::test]
async fn read_only_runs_concurrently() {
    let rec = Arc::new(Recorder::default());
    let tools: Vec<Arc<dyn Tool>> = vec![
        Arc::new(ReadOnlyTool { label: "ro1", sleep_ms: 60, rec: rec.clone() }),
        Arc::new(ReadOnlyTool { label: "ro2", sleep_ms: 60, rec: rec.clone() }),
        Arc::new(ReadOnlyTool { label: "ro3", sleep_ms: 60, rec: rec.clone() }),
    ];
    let plan = build_plan(vec![step("ro1"), step("ro2"), step("ro3")]);
    let mut provider = CannedProvider { plan };
    let mut renderer = NdjsonRender { out: Vec::<u8>::new() };
    let mut perms = AlwaysAllow;

    run_turn(
        "task",
        &tools,
        &cwd(),
        &mut renderer,
        &mut provider,
        None,
        &mut perms,
        TurnConfig::default(),
        true,
    )
    .await
    .unwrap();

    let spans = rec.snapshot();
    assert_eq!(spans.len(), 3);
    // All three should overlap meaningfully — the last start should occur
    // before the first end (i.e. they're concurrent).
    let mut starts: Vec<_> = spans.iter().map(|(_, s, _)| *s).collect();
    let mut ends: Vec<_> = spans.iter().map(|(_, _, e)| *e).collect();
    starts.sort();
    ends.sort();
    let last_start = starts[2];
    let first_end = ends[0];
    assert!(
        last_start < first_end,
        "expected concurrent execution, last_start >= first_end ({:?} vs {:?})",
        last_start,
        first_end
    );
    assert_eq!(rec.peak.load(Ordering::SeqCst), 3);
}

#[tokio::test]
async fn mutating_runs_serially_in_order() {
    let rec = Arc::new(Recorder::default());
    let tools: Vec<Arc<dyn Tool>> = vec![
        Arc::new(MutatingTool { label: "mut1", sleep_ms: 30, rec: rec.clone() }),
        Arc::new(MutatingTool { label: "mut2", sleep_ms: 30, rec: rec.clone() }),
    ];
    let plan = build_plan(vec![step("mut1"), step("mut2")]);
    let mut provider = CannedProvider { plan };
    let mut renderer = NdjsonRender { out: Vec::<u8>::new() };
    let mut perms = AlwaysAllow;

    run_turn(
        "task",
        &tools,
        &cwd(),
        &mut renderer,
        &mut provider,
        None,
        &mut perms,
        TurnConfig::default(),
        true,
    )
    .await
    .unwrap();

    let spans = rec.snapshot();
    assert_eq!(spans.len(), 2);
    // Plan-order: mut1 first, then mut2; non-overlapping.
    assert_eq!(spans[0].0, "mut1");
    assert_eq!(spans[1].0, "mut2");
    assert!(
        spans[0].2 <= spans[1].1,
        "mut1 end ({:?}) must precede mut2 start ({:?})",
        spans[0].2,
        spans[1].1
    );
}

struct DenyIdx {
    deny_step_idx: usize,
    counter: AtomicUsize,
}

impl PermissionCheck for DenyIdx {
    fn check(&mut self, _name: &str, _args: &Value) -> (bool, String) {
        let n = self.counter.fetch_add(1, Ordering::SeqCst);
        if n == self.deny_step_idx {
            (false, "blocked".into())
        } else {
            (true, "ok".into())
        }
    }
}

#[tokio::test]
async fn denied_step_does_not_block_siblings() {
    let rec = Arc::new(Recorder::default());
    let tools: Vec<Arc<dyn Tool>> = vec![
        Arc::new(ReadOnlyTool { label: "ro1", sleep_ms: 10, rec: rec.clone() }),
        Arc::new(ReadOnlyTool { label: "ro2", sleep_ms: 10, rec: rec.clone() }),
        Arc::new(ReadOnlyTool { label: "ro3", sleep_ms: 10, rec: rec.clone() }),
    ];
    let plan = build_plan(vec![step("ro1"), step("ro2"), step("ro3")]);
    let mut provider = CannedProvider { plan };
    let mut renderer = NdjsonRender { out: Vec::<u8>::new() };
    let mut perms = DenyIdx { deny_step_idx: 1, counter: AtomicUsize::new(0) };

    let result = run_turn(
        "task",
        &tools,
        &cwd(),
        &mut renderer,
        &mut provider,
        None,
        &mut perms,
        TurnConfig::default(),
        true,
    )
    .await
    .unwrap();

    // Steps 0 and 2 ran; step 1 was denied.
    let spans = rec.snapshot();
    let labels: Vec<&str> = spans.iter().map(|(l, _, _)| l.as_str()).collect();
    assert!(labels.contains(&"ro1"));
    assert!(labels.contains(&"ro3"));
    assert!(!labels.contains(&"ro2"), "denied step ran: {labels:?}");

    assert!(result.tool_results[1].contains("denied"));
}

#[tokio::test]
async fn unknown_tool_is_error() {
    let tools: Vec<Arc<dyn Tool>> = vec![Arc::new(ReadOnlyTool {
        label: "ro1",
        sleep_ms: 0,
        rec: Arc::new(Recorder::default()),
    })];
    let plan = build_plan(vec![step("ro1"), step("does_not_exist")]);
    let mut provider = CannedProvider { plan };
    let mut renderer = NdjsonRender { out: Vec::<u8>::new() };
    let mut perms = AlwaysAllow;

    let result = run_turn(
        "task",
        &tools,
        &cwd(),
        &mut renderer,
        &mut provider,
        None,
        &mut perms,
        TurnConfig::default(),
        true,
    )
    .await
    .unwrap();

    assert!(result.tool_results[1].contains("<error: unknown tool"));
}

#[tokio::test]
async fn parallel_cap_respected() {
    let rec = Arc::new(Recorder::default());
    let tools: Vec<Arc<dyn Tool>> = (0..10)
        .map(|i| {
            let label: &'static str = Box::leak(format!("ro{i}").into_boxed_str());
            Arc::new(ReadOnlyTool {
                label,
                sleep_ms: 30,
                rec: rec.clone(),
            }) as Arc<dyn Tool>
        })
        .collect();
    let plan = build_plan(
        (0..10)
            .map(|i| step(Box::leak(format!("ro{i}").into_boxed_str())))
            .collect(),
    );
    let mut provider = CannedProvider { plan };
    let mut renderer = NdjsonRender { out: Vec::<u8>::new() };
    let mut perms = AlwaysAllow;

    let cfg = TurnConfig {
        parallel_cap: 3,
        ..TurnConfig::default()
    };
    run_turn(
        "task",
        &tools,
        &cwd(),
        &mut renderer,
        &mut provider,
        None,
        &mut perms,
        cfg,
        true,
    )
    .await
    .unwrap();

    let peak = rec.peak.load(Ordering::SeqCst);
    assert!(peak <= 3, "peak concurrency {peak} exceeded cap of 3");
    assert!(peak >= 1, "no executions recorded");
}
