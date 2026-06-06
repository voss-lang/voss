//! Content-hash line anchors (hashline edits).
//!
//! A line's anchor is the first 8 hex chars of SHA-256 of the line's raw
//! content (no trailing newline). The canonical line list is `text.split('\n')`
//! everywhere — read annotation, edit resolution, and hashing — so anchors a
//! model copies from an annotated `fs_read` resolve identically in `fs_edit`,
//! including for CRLF files (the `\r` is part of the hashed segment on both
//! sides).

use sha2::{Digest, Sha256};

/// 8-hex-char content anchor for a single line (newline excluded).
pub fn line_anchor(line: &str) -> String {
    let digest = Sha256::digest(line.as_bytes());
    let mut s = String::with_capacity(8);
    for b in &digest[..4] {
        s.push_str(&format!("{b:02x}"));
    }
    s
}

/// Render file text with a per-line `{anchor}│{line}` gutter. A trailing empty
/// segment (file ended with `\n`) is not emitted — it is never an edit target.
pub fn annotate(text: &str) -> String {
    let segs: Vec<&str> = text.split('\n').collect();
    let n = segs.len();
    let mut out = String::with_capacity(text.len() + n * 10);
    for (i, seg) in segs.iter().enumerate() {
        if i + 1 == n && seg.is_empty() {
            break;
        }
        out.push_str(&line_anchor(seg));
        out.push('│');
        out.push_str(seg);
        out.push('\n');
    }
    out
}

/// Resolve an anchor to a unique line index in `segs`. Mirrors the
/// zero/multi-match error shape of `old`-based edits.
pub fn resolve(segs: &[&str], anchor: &str) -> Result<usize, String> {
    let hits: Vec<usize> = segs
        .iter()
        .enumerate()
        .filter(|(_, l)| line_anchor(l) == anchor)
        .map(|(i, _)| i)
        .collect();
    match hits.len() {
        0 => Err(format!(
            "anchor `{anchor}` not found (stale — re-read with annotate=true)"
        )),
        1 => Ok(hits[0]),
        _ => {
            let lns: Vec<String> = hits.iter().map(|i| (i + 1).to_string()).collect();
            Err(format!(
                "anchor `{anchor}` matches lines {} — ambiguous, use `old` instead",
                lns.join(",")
            ))
        }
    }
}
