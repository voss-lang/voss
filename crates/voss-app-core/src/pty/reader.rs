use std::collections::VecDeque;
use std::io::Read;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::pty::commands::{BudgetData, ContextData, PtyEvent, VossCmdData};
use crate::pty::PtyRegistry;

const BUDGET_PREFIX: &[u8] = b"\x1b]1337;voss-budget=";
const CONTEXT_PREFIX: &[u8] = b"\x1b]1337;voss-context=";

/// Command-output evidence cap (S3.2): 256 KiB total = 192 KiB head + 64 KiB tail.
const OUTPUT_HEAD_CAP: usize = 192 * 1024;
const OUTPUT_TAIL_CAP: usize = 64 * 1024;

/// Scans `data` for one complete `{prefix}{json}BEL` OSC 1337 sequence.
/// Returns `Some((json_bytes, display_bytes))` if the full sequence is present;
/// `None` passes through the buffer unchanged as display bytes.
/// Buffer fragmentation: returns `None` silently — next emission has cumulative
pub(crate) fn extract_voss_osc(data: &[u8], prefix: &[u8]) -> Option<(Vec<u8>, Vec<u8>)> {
    let start = data.windows(prefix.len()).position(|w| w == prefix)?;
    let json_start = start + prefix.len();
    let rel_end = data[json_start..].iter().position(|&b| b == 0x07)?;
    let end = json_start + rel_end;
    let json_bytes = data[json_start..end].to_vec();
    let mut display = data[..start].to_vec();
    display.extend_from_slice(&data[end + 1..]);
    Some((json_bytes, display))
}

/// Shell-integration marks (S3): OSC 133 A/B/C/D, OSC 7 cwd, and the
/// `voss-cmd` metadata OSC emitted by the `voss shell-init` hooks.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum ShellMark {
    PromptStart,
    PromptEnd,
    CommandStart,
    CommandEnd(i32),
    Cwd(String),
    CommandMeta(VossCmdData),
}

/// Ordered scan result: marks interleaved with the display bytes between them,
/// so capture boundaries stay exact when several marks share one read.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum ScanItem {
    Mark(ShellMark),
    Display(Vec<u8>),
}

fn parse_shell_mark(body: &[u8]) -> Option<ShellMark> {
    if body == b"133;A" || body.starts_with(b"133;A;") {
        return Some(ShellMark::PromptStart);
    }
    if body == b"133;B" || body.starts_with(b"133;B;") {
        return Some(ShellMark::PromptEnd);
    }
    if body == b"133;C" || body.starts_with(b"133;C;") {
        return Some(ShellMark::CommandStart);
    }
    if body == b"133;D" {
        return Some(ShellMark::CommandEnd(0));
    }
    if let Some(rest) = body.strip_prefix(b"133;D;") {
        let code = rest
            .split(|&b| b == b';')
            .next()
            .and_then(|f| std::str::from_utf8(f).ok())
            .and_then(|s| s.parse().ok())
            .unwrap_or(0);
        return Some(ShellMark::CommandEnd(code));
    }
    if let Some(rest) = body.strip_prefix(b"7;") {
        let uri = String::from_utf8_lossy(rest);
        let no_scheme = uri.strip_prefix("file://").unwrap_or(&uri);
        let path = match no_scheme.find('/') {
            Some(idx) => &no_scheme[idx..],
            None => no_scheme,
        };
        return Some(ShellMark::Cwd(path.to_string()));
    }
    if let Some(rest) = body.strip_prefix(b"1337;voss-cmd=") {
        let meta: VossCmdData = serde_json::from_slice(rest).ok()?;
        return Some(ShellMark::CommandMeta(meta));
    }
    None
}

/// Scans `data` for OSC sequences terminated by BEL or ST. Recognized shell
/// marks are extracted; unknown or unterminated sequences pass through as
/// display bytes (same fragmentation stance as `extract_voss_osc`).
pub(crate) fn scan_shell_marks(data: &[u8]) -> Vec<ScanItem> {
    let mut items = Vec::new();
    let mut display: Vec<u8> = Vec::new();
    let mut i = 0;
    while i < data.len() {
        if data[i] == 0x1b && i + 1 < data.len() && data[i + 1] == b']' {
            let body_start = i + 2;
            let mut term = None;
            let mut j = body_start;
            while j < data.len() {
                if data[j] == 0x07 {
                    term = Some((j, 1));
                    break;
                }
                if data[j] == 0x1b && j + 1 < data.len() && data[j + 1] == b'\\' {
                    term = Some((j, 2));
                    break;
                }
                j += 1;
            }
            let Some((end, tlen)) = term else {
                display.extend_from_slice(&data[i..]);
                break;
            };
            match parse_shell_mark(&data[body_start..end]) {
                Some(mark) => {
                    if !display.is_empty() {
                        items.push(ScanItem::Display(std::mem::take(&mut display)));
                    }
                    items.push(ScanItem::Mark(mark));
                }
                None => display.extend_from_slice(&data[i..end + tlen]),
            }
            i = end + tlen;
        } else {
            display.push(data[i]);
            i += 1;
        }
    }
    if !display.is_empty() {
        items.push(ScanItem::Display(display));
    }
    items
}

#[derive(Default)]
pub(crate) struct OscBuffer {
    pending: Vec<u8>,
}

impl OscBuffer {
    pub(crate) fn push(&mut self, data: &[u8]) -> Vec<u8> {
        self.pending.extend_from_slice(data);
        let mut i = 0;
        while i < self.pending.len() {
            if self.pending[i] != 0x1b {
                i += 1;
                continue;
            }
            if i + 1 == self.pending.len() {
                break;
            }
            if self.pending[i + 1] != b']' {
                i += 2;
                continue;
            }
            let mut end = i + 2;
            while end < self.pending.len() && self.pending[end] != 0x07
                && !(self.pending[end] == 0x1b && self.pending.get(end + 1) == Some(&b'\\')) {
                end += 1;
            }
            if end == self.pending.len() {
                break;
            }
            i = end + if self.pending[end] == 0x07 { 1 } else { 2 };
        }
        // A malformed/oversize OSC must not hide terminal output indefinitely.
        if self.pending.len() - i > 64 * 1024 {
            i = self.pending.len();
        }
        self.pending.drain(..i).collect()
    }

    fn finish(&mut self) -> Vec<u8> {
        std::mem::take(&mut self.pending)
    }
}

struct Capture {
    cmd_id: String,
    argv_text: String,
    cwd: String,
    started: Option<std::time::Instant>,
    head: Vec<u8>,
    tail: VecDeque<u8>,
    truncated: bool,
}

impl Capture {
    fn new(cwd: Option<String>, started: Option<std::time::Instant>) -> Self {
        Self {
            cmd_id: String::new(),
            argv_text: String::new(),
            cwd: cwd.unwrap_or_default(),
            started,
            head: Vec::new(),
            tail: VecDeque::new(),
            truncated: false,
        }
    }

    fn push(&mut self, mut bytes: &[u8]) {
        if self.head.len() < OUTPUT_HEAD_CAP {
            let take = (OUTPUT_HEAD_CAP - self.head.len()).min(bytes.len());
            self.head.extend_from_slice(&bytes[..take]);
            bytes = &bytes[take..];
        }
        for &b in bytes {
            if self.tail.len() == OUTPUT_TAIL_CAP {
                self.tail.pop_front();
                self.truncated = true;
            }
            self.tail.push_back(b);
        }
    }

    fn output(&mut self) -> Vec<u8> {
        let mut out = std::mem::take(&mut self.head);
        out.extend(self.tail.drain(..));
        out
    }
}

/// Stateful OSC 133 tracker: one open capture between `133;C` and `133;D`.
#[derive(Default)]
pub(crate) struct CommandTracker {
    cwd: Option<String>,
    capture: Option<Capture>,
}

impl CommandTracker {
    pub(crate) fn apply(&mut self, mark: &ShellMark) -> Vec<PtyEvent> {
        match mark {
            ShellMark::PromptStart | ShellMark::PromptEnd => vec![],
            ShellMark::Cwd(path) => {
                self.cwd = Some(path.clone());
                vec![]
            }
            ShellMark::CommandStart => {
                self.capture = Some(Capture::new(self.cwd.clone(), Some(std::time::Instant::now())));
                vec![]
            }
            ShellMark::CommandMeta(meta) => {
                match self.capture.as_mut() {
                    Some(c) => {
                        c.cmd_id = meta.cmd_id.clone();
                        c.argv_text = meta.argv_text.clone();
                        c.cwd = meta.cwd.clone();
                    }
                    // voss-cmd without a preceding 133;C (fragmented read):
                    // capture with no start time, so duration_ms reports 0.
                    None => {
                        let mut c = Capture::new(None, None);
                        c.cmd_id = meta.cmd_id.clone();
                        c.argv_text = meta.argv_text.clone();
                        c.cwd = meta.cwd.clone();
                        self.capture = Some(c);
                    }
                }
                vec![PtyEvent::CommandStarted {
                    cmd_id: meta.cmd_id.clone(),
                    argv_text: meta.argv_text.clone(),
                    cwd: meta.cwd.clone(),
                    at: iso8601_now(),
                }]
            }
            ShellMark::CommandEnd(exit) => {
                let Some(mut c) = self.capture.take() else {
                    return vec![];
                };
                let duration_ms = c
                    .started
                    .map(|t| t.elapsed().as_millis() as u64)
                    .unwrap_or(0);
                let truncated = c.truncated;
                let output = c.output();
                vec![PtyEvent::CommandFinished {
                    cmd_id: c.cmd_id,
                    exit: *exit,
                    duration_ms,
                    output,
                    truncated,
                }]
            }
        }
    }

    pub(crate) fn capture_bytes(&mut self, bytes: &[u8]) {
        if let Some(c) = self.capture.as_mut() {
            c.push(bytes);
        }
    }
}

/// Current UTC time as an ISO 8601 string (no chrono dep in this crate).
fn iso8601_now() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let days = (secs / 86_400) as i64;
    let rem = secs % 86_400;
    let (h, mi, s) = (rem / 3600, (rem % 3600) / 60, rem % 60);
    // civil-from-days (Howard Hinnant's algorithm)
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let mo = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if mo <= 2 { y + 1 } else { y };
    format!("{y:04}-{mo:02}-{d:02}T{h:02}:{mi:02}:{s:02}Z")
}

/// Route display-bound bytes through the shell-mark scanner: emit command
/// events, feed the open capture, forward the remainder as `PtyEvent::Data`.
/// Returns false when the channel is closed (caller breaks the loop).
fn emit_display(
    data: &[u8],
    tracker: &mut CommandTracker,
    on_data: &tauri::ipc::Channel<PtyEvent>,
) -> bool {
    let mut display: Vec<u8> = Vec::new();
    for item in scan_shell_marks(data) {
        match item {
            ScanItem::Display(bytes) => {
                tracker.capture_bytes(&bytes);
                display.extend_from_slice(&bytes);
            }
            ScanItem::Mark(mark) => {
                for ev in tracker.apply(&mark) {
                    let _ = on_data.send(ev);
                }
            }
        }
    }
    display.is_empty()
        || on_data.send(PtyEvent::Data { bytes: display }).is_ok()
}

/// Start the blocking read loop for `session_id`. On EOF/err it emits
/// `PtyEvent::Exit` with the real exit code, reaps the child, and removes the
pub fn start_reader(
    session_id: String,
    mut reader: Box<dyn Read + Send>,
    mut pause_rx: tokio::sync::mpsc::Receiver<bool>,
    on_data: tauri::ipc::Channel<PtyEvent>,
    registry: Arc<PtyRegistry>,
) {
    tokio::task::spawn_blocking(move || {
        let mut buf = [0u8; 8192];
        let mut tracker = CommandTracker::default();
        let mut osc = OscBuffer::default();
        loop {
            // Non-blocking backpressure check; if paused, block until resumed.
            if let Ok(true) = pause_rx.try_recv() {
                while pause_rx.blocking_recv() != Some(false) {}
            }
            match reader.read(&mut buf) {
                Ok(0) => break, // EOF — child exited
                Ok(n) => {
                    let data = osc.push(&buf[..n]);
                    let slice = data.as_slice();
                    // Budget OSC check
                    if let Some((json_bytes, display_bytes)) =
                        extract_voss_osc(slice, BUDGET_PREFIX)
                    {
                        if let Ok(data) = serde_json::from_slice::<BudgetData>(&json_bytes) {
                            let _ = on_data.send(PtyEvent::BudgetUpdate(data));
                        }
                        if !emit_display(&display_bytes, &mut tracker, &on_data) {
                            break;
                        }
                        continue;
                    }
                    // Context OSC check
                    if let Some((json_bytes, display_bytes)) =
                        extract_voss_osc(slice, CONTEXT_PREFIX)
                    {
                        if let Ok(data) = serde_json::from_slice::<ContextData>(&json_bytes) {
                            let _ = on_data.send(PtyEvent::ContextUpdate(data));
                        }
                        if !emit_display(&display_bytes, &mut tracker, &on_data) {
                            break;
                        }
                        continue;
                    }
                    if !emit_display(slice, &mut tracker, &on_data) {
                        break; // channel closed (pane gone)
                    }
                }
                Err(_) => break,
            }
        }

        emit_display(&osc.finish(), &mut tracker, &on_data);

        let code = registry
            .get(&session_id)
            .and_then(|s| {
                let c = s.try_exit_code();
                let _ = s.kill();
                c
            })
            .unwrap_or(0);
        let _ = on_data.send(PtyEvent::Exit { code });
        registry.remove(&session_id);
    });
}
