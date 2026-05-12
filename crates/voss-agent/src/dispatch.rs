//! D-11..D-14 step dispatch. Read-only tools fan out concurrently (cap N);
//! mutating tools execute serially in plan order. Permission gate consulted
//! per step before scheduling. Denial of one step does not block siblings.

use std::sync::atomic::AtomicBool;
use std::sync::Arc;

use futures::future::join_all;
use voss_render::{Render, ToolState};
use voss_tools::Tool;

use crate::run_turn::{cancelled, PermissionCheck};
use crate::ToolCall;

struct Resolved {
    idx: usize,
    name: String,
    args: serde_json::Value,
    tool: Option<Arc<dyn Tool>>,
    denied_reason: Option<String>,
}

pub(crate) async fn dispatch_steps(
    steps: &[ToolCall],
    tools: &[Arc<dyn Tool>],
    renderer: &mut dyn Render,
    perms: &mut dyn PermissionCheck,
    parallel_cap: usize,
    cancel: Option<Arc<AtomicBool>>,
) -> Vec<String> {
    let mut results: Vec<Option<String>> = vec![None; steps.len()];

    // Resolve each step + consult gate up-front (D-14).
    let mut resolved: Vec<Resolved> = Vec::with_capacity(steps.len());
    for (i, step) in steps.iter().enumerate() {
        let args = serde_json::Value::Object(step.args.clone());
        let tool = tools.iter().find(|t| t.name() == step.name).cloned();
        let denied_reason = if tool.is_some() {
            let (allowed, reason) = perms.check(&step.name, &args);
            if allowed {
                None
            } else {
                Some(reason)
            }
        } else {
            None
        };
        resolved.push(Resolved {
            idx: i,
            name: step.name.clone(),
            args,
            tool,
            denied_reason,
        });
    }

    // Fill unknown-tool + denial slots up front so renderer ordering follows
    // plan order on the failure path.
    for r in &resolved {
        if r.tool.is_none() {
            renderer.show_tool_call(&r.name, &r.args, "<unknown tool>", ToolState::Error);
            results[r.idx] = Some(format!("<error: unknown tool {:?}>", r.name));
        } else if let Some(reason) = &r.denied_reason {
            let text = format!("<denied: {reason}>");
            renderer.show_tool_call(&r.name, &r.args, &text, ToolState::Error);
            results[r.idx] = Some(text);
        }
    }

    // Partition the still-unresolved into read-only (parallel) vs mutating (serial).
    let live: Vec<&Resolved> = resolved
        .iter()
        .filter(|r| r.tool.is_some() && r.denied_reason.is_none() && results[r.idx].is_none())
        .collect();
    let (parallel, serial): (Vec<&Resolved>, Vec<&Resolved>) = live
        .into_iter()
        .partition(|r| !r.tool.as_ref().unwrap().is_mutating());

    // D-13: read-only group first, with concurrency cap. Print "running…"
    // for the chunk, await all, then print final state per-step in plan order.
    let cap = parallel_cap.max(1);
    for chunk in parallel.chunks(cap) {
        for r in chunk {
            renderer.show_tool_call(&r.name, &r.args, "running…", ToolState::Pending);
        }
        let futs: Vec<_> = chunk
            .iter()
            .map(|r| {
                let t = r.tool.clone().unwrap();
                let args = r.args.clone();
                let idx = r.idx;
                async move { (idx, t.invoke(args).await) }
            })
            .collect();
        let outs = join_all(futs).await;
        // Sort outs by idx so renderer events match plan order within chunk.
        let mut outs = outs;
        outs.sort_by_key(|(idx, _)| *idx);
        for (idx, res) in outs {
            let text = match res {
                Ok(s) => s,
                Err(e) => format!("<error: {e}>"),
            };
            let r = resolved.iter().find(|x| x.idx == idx).unwrap();
            let summary = summarize(&text, 80);
            let state = if text.starts_with("<error") {
                ToolState::Error
            } else {
                ToolState::Ok
            };
            renderer.show_tool_call(&r.name, &r.args, &summary, state);
            results[idx] = Some(text);
        }
    }

    // Mutating: serial in plan order.
    for r in serial {
        renderer.show_tool_call(&r.name, &r.args, "running…", ToolState::Pending);
        let t = r.tool.clone().unwrap();
        let res = t.invoke(r.args.clone()).await;
        let text = match res {
            Ok(s) => s,
            Err(e) => format!("<error: {e}>"),
        };
        let summary = summarize(&text, 80);
        let state = if text.starts_with("<error") {
            ToolState::Error
        } else {
            ToolState::Ok
        };
        renderer.show_tool_call(&r.name, &r.args, &summary, state);
        results[r.idx] = Some(text);
    }

    results.into_iter().map(|x| x.unwrap_or_default()).collect()
}

fn summarize(text: &str, limit: usize) -> String {
    let first = text.lines().next().unwrap_or("");
    if first.is_empty() {
        return format!("({}B)", text.len());
    }
    if first.chars().count() > limit {
        let cut: String = first.chars().take(limit - 1).collect();
        format!("{cut}…")
    } else {
        first.to_string()
    }
}
