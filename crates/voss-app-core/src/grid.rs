//! A3 binary-split grid mirror — the in-memory Rust reflection of the Solid
//! source-of-truth tree (GRD-08). NO disk I/O in A3: this is memory-only;
//! A4 adds `name`, A6 serializes the whole struct to `session.json`.
//!
//! serde uses `rename_all = "camelCase"` on every struct/enum that carries
//! multi-word or TS-aligned keys so the JSON round-trips the `tree.ts` field
//! names exactly (`focusedId`, `kind`, `orientation`, `ratio`, `left`,
//! `right`, `id`, `cwd`, `shell`, `index`). `Orientation` is intentionally
//! NOT renamed: its variants must serialize as the literal `"H"` / `"V"` the
//! TypeScript model uses.

use std::sync::Mutex;

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "camelCase")]
pub enum TreeNode {
    Split(SplitNode),
    Pane(PaneLeaf),
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SplitNode {
    pub orientation: Orientation,
    pub ratio: f32,
    pub left: Box<TreeNode>,
    pub right: Box<TreeNode>,
}

/// Not `rename_all`'d — variants serialize as the literal `"H"` / `"V"`
/// matching the TypeScript `orientation` union.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub enum Orientation {
    H,
    V,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PaneLeaf {
    pub id: String,
    pub cwd: String,
    pub shell: String,
    pub index: u32,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GridState {
    pub root: TreeNode,
    pub focused_id: String,
}

/// Single default pane — initializes the managed mirror before the webview's
/// first `sync_grid` (overwritten on the first structural change). In-memory
/// only; no disk seed (GRD-08).
impl Default for GridState {
    fn default() -> Self {
        GridState {
            root: TreeNode::Pane(PaneLeaf {
                id: "root".into(),
                cwd: String::new(),
                shell: String::new(),
                index: 1,
            }),
            focused_id: "root".into(),
        }
    }
}

/// Plain mirror mutators — the cross-crate seam. `tauri::generate_handler!`
/// can only resolve the command helper macros generated in the SAME crate,
/// so the app crate registers its own thin `#[tauri::command]` wrappers
/// (src-tauri/src/lib.rs) that delegate here (same pattern A2-05 used for
/// PTY). Pure in-memory, no filesystem (GRD-08).
pub fn overwrite(slot: &Mutex<GridState>, new_state: GridState) -> Result<(), String> {
    let mut guard = slot
        .lock()
        .map_err(|e| format!("grid state mutex poisoned: {e}"))?;
    *guard = new_state;
    Ok(())
}

/// Clone the in-memory mirror for read-back (parity testing only — no disk).
pub fn snapshot(slot: &Mutex<GridState>) -> Result<GridState, String> {
    let guard = slot
        .lock()
        .map_err(|e| format!("grid state mutex poisoned: {e}"))?;
    Ok(guard.clone())
}

/// Overwrite the in-memory grid mirror with the webview's latest tree
/// (GRD-08). In-memory ONLY — no filesystem access.
#[tauri::command]
pub fn sync_grid(
    state: tauri::State<'_, Mutex<GridState>>,
    new_state: GridState,
) -> Result<(), String> {
    overwrite(state.inner(), new_state)
}

/// Read-back of the in-memory mirror for Solid↔Rust parity assertions
/// (GRD-08). In-memory ONLY — no filesystem access.
#[tauri::command]
pub fn get_grid(state: tauri::State<'_, Mutex<GridState>>) -> Result<GridState, String> {
    snapshot(state.inner())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pane(id: &str, idx: u32) -> TreeNode {
        TreeNode::Pane(PaneLeaf {
            id: id.into(),
            cwd: "/tmp".into(),
            shell: "zsh".into(),
            index: idx,
        })
    }

    fn split(o: Orientation, l: TreeNode, r: TreeNode) -> TreeNode {
        TreeNode::Split(SplitNode {
            orientation: o,
            ratio: 0.5,
            left: Box::new(l),
            right: Box::new(r),
        })
    }

    #[test]
    fn grid_state_2x2_round_trips_through_serde_json() {
        // V[ H[a,b], H[c,d] ]
        let original = GridState {
            root: split(
                Orientation::V,
                split(Orientation::H, pane("a", 1), pane("b", 2)),
                split(Orientation::H, pane("c", 3), pane("d", 4)),
            ),
            focused_id: "a".into(),
        };
        let json = serde_json::to_string(&original).expect("serialize");
        let back: GridState = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(original, back, "2x2 GridState must round-trip");
    }

    #[test]
    fn json_keys_match_typescript_field_names() {
        let s = GridState {
            root: pane("x", 1),
            focused_id: "x".into(),
        };
        let json = serde_json::to_string(&s).unwrap();
        // camelCase + literal kind/orientation values matching tree.ts
        assert!(json.contains("\"focusedId\""), "focusedId key: {json}");
        assert!(json.contains("\"kind\":\"pane\""), "pane tag: {json}");

        let with_split = GridState {
            root: split(Orientation::H, pane("a", 1), pane("b", 2)),
            focused_id: "a".into(),
        };
        let j2 = serde_json::to_string(&with_split).unwrap();
        assert!(j2.contains("\"kind\":\"split\""), "split tag: {j2}");
        assert!(j2.contains("\"orientation\":\"H\""), "H literal: {j2}");
    }
}
